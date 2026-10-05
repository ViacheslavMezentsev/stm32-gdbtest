"""Read-only run profile: target.toml mapping, sections, dotted paths and value origins."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest.configuration import DEFAULTS, Configuration, freeze
from stm32_gdbtest.run_profile import Profile

TARGET = dict(mcu="STM32F030R8", flash_start=0x08000000, breakpoint_limit=4, fault_handlers=[])
VIRTUAL = dict(target=TARGET, image=dict(image=dict(mode="flash")),
               api=dict(schema=1, records={**DEFAULTS, 'custom': 999}, user=dict(count=3),
                        reset=dict(command="monitor reset halt")))
BOARD = dict(board=dict(name="NUCLEO-F030R8", led="PA5"))
VIRTUAL["data"] = dict(board=BOARD)
BUILD = dict(compilers=[dict(name="arm-none-eabi-gcc", version="13.3.1")], cube_packages=[],
             libraries={"CM0_CMSIS": "5.6"}, defines=["STM32F030x8"], sources=["src/app.c"])
PROPS = dict(target=dict(sha256="t" * 64, reference="target.toml", data=TARGET),
             **{"data.board": dict(sha256="b" * 64, reference="board.toml", data=BOARD)},
             api=dict(sha256="a" * 64, reference="api.toml",
                      data=dict(schema=1, user=dict(count=3), reset=dict(command="monitor reset halt"))),
             image=None)
CASE = dict(id="HW_CI_PROFILE", function="profile", timeout_s=30, labels=("api",), contracts=())
STAND = dict(backend="openocd", server="local", speed_khz=4000, flash="gdb_load")


def configuration(props=PROPS, session="s" * 64):
    return Configuration(freeze(VIRTUAL), freeze(props), session, {})


class ProfileTests(unittest.TestCase):
    def profile(self, **options):
        options.setdefault("case", CASE)
        options.setdefault("stand", STAND)
        options.setdefault("gdb", dict(version="15.2", stop_details=None))
        options.setdefault("build", BUILD)
        return Profile(TARGET, options.pop("configuration", configuration()), **options)

    def test_indexing_reads_target_toml_as_before(self):
        profile = self.profile()
        self.assertEqual(profile["flash_start"], 0x08000000)
        self.assertEqual(set(profile), set(TARGET))
        self.assertEqual(len(profile), len(TARGET))
        self.assertIs(profile.get("nonexistent"), None)
        self.assertEqual(profile.get("mcu"), "STM32F030R8")

    def test_sections_and_dotted_paths(self):
        profile = self.profile()
        self.assertEqual(profile.user["count"], 3)
        self.assertEqual(profile.get("user.count"), 3)
        self.assertEqual(profile.get("api.reset.command"), "monitor reset halt")
        self.assertEqual(profile.get("api.records.custom"), 999)
        self.assertEqual(profile.get("api.frames.limit"), Profile.__init__.__globals__["FRAMES_LIMIT"])
        self.assertEqual(profile.image["mode"], "flash")
        self.assertEqual(profile.get("case.id"), "HW_CI_PROFILE")
        self.assertEqual(profile.get("stand.backend"), "openocd")
        self.assertEqual(profile.get("gdb.version"), "15.2")
        self.assertEqual(profile.files["api"]["sha256"], "a" * 64)
        self.assertEqual(profile.files["session"]["reference"], "session.toml")
        self.assertNotIn("image", profile.files)
        self.assertEqual(profile.get("user.missing", 7), 7)
        self.assertIsNone(profile.get(""))

    def test_every_section_is_read_only(self):
        profile = self.profile()
        for name in ("target", "api", "user", "files", "case", "stand", "gdb"):
            with self.subTest(section=name), self.assertRaises(TypeError):
                getattr(profile, name)["x"] = 1
        with self.assertRaises(TypeError):
            profile.api["records"]["max_records"] = 1
        with self.assertRaises(AttributeError):
            profile.user = {}
        with self.assertRaises(TypeError):
            profile["mcu"] = "other"

    def test_origin_of_values(self):
        profile = self.profile()
        self.assertEqual(dict(profile.origin("mcu")),
                         dict(state="file", file="target.toml", sha256="t" * 64))
        self.assertEqual(profile.origin("user.count")["file"], "api.toml")
        self.assertEqual(dict(profile.origin("api.frames.limit")), dict(state="default"))
        self.assertEqual(dict(profile.origin("case.id")), dict(state="run", section="case"))
        with patch.dict("os.environ", STM32_GDBTEST_RESET_COMMAND="monitor reset"):
            self.assertEqual(profile.origin("api.reset.command")["state"], "override")
        with self.assertRaises(KeyError):
            profile.origin("user.missing")
        with self.assertRaises(KeyError):
            profile.origin("")

    def test_data_files_and_build(self):
        profile = self.profile()
        self.assertEqual(profile.data["board"]["board"]["led"], "PA5")
        self.assertEqual(profile.get("data.board.board.name"), "NUCLEO-F030R8")
        self.assertEqual(dict(profile.origin("data.board.board.led")),
                         dict(state="file", file="board.toml", sha256="b" * 64))
        self.assertEqual(profile.files["data.board"]["reference"], "board.toml")
        self.assertEqual(profile.build["libraries"]["CM0_CMSIS"], "5.6")
        self.assertEqual(profile.get("build.defines"), ("STM32F030x8",))
        self.assertEqual(dict(profile.origin("build.defines")), dict(state="run", section="build"))
        with self.assertRaises(TypeError):
            profile.data["board"]["board"]["led"] = "PA6"
        bare = self.profile(build=None, configuration=configuration(props=dict(PROPS, **{"data.board": None})))
        self.assertIsNone(bare.build)

    def test_gdb_section_is_live_and_snapshot_is_plain(self):
        profile = self.profile()
        view = profile.gdb
        profile._observe_gdb(stop_details=True)
        self.assertTrue(view["stop_details"])
        plain = profile.snapshot()
        self.assertEqual(set(plain), {"target", "api", "image", "data", "files", "build", "case", "stand", "gdb"})
        self.assertEqual(plain["case"]["labels"], ["api"])
        self.assertIsInstance(plain["api"]["records"], dict)

    def test_without_configuration(self):
        profile = Profile(TARGET)
        self.assertEqual(profile.api["schema"], 1)
        self.assertEqual(profile.api["records"]["max_records"], DEFAULTS["max_records"])
        self.assertEqual(dict(profile.files), {})
        self.assertEqual(dict(profile.data), {})
        self.assertIsNone(profile.build)
        self.assertEqual(dict(profile.origin("api.schema")), dict(state="default"))


class TargetProfileTests(unittest.TestCase):
    def setUp(self):
        fake = types.SimpleNamespace(events=types.SimpleNamespace(stop=Mock()), VERSION="15.2",
                                     history_count=lambda: 0)
        previous = sys.modules.pop('stm32_gdbtest.target', None)
        with patch.dict(sys.modules, gdb=fake):
            self.module = importlib.import_module('stm32_gdbtest.target')
        sys.modules.pop('stm32_gdbtest.target', None)
        if previous is not None:
            sys.modules['stm32_gdbtest.target'] = previous

    def test_target_builds_the_profile_from_the_run(self):
        target = self.module.Target({"checks": []}, TARGET, configuration(),
                                    context=dict(case=CASE, stand=STAND))
        self.assertIsInstance(target.profile, Profile)
        self.assertEqual(target.profile["mcu"], "STM32F030R8")
        self.assertEqual(target.profile.case["id"], "HW_CI_PROFILE")
        self.assertEqual(target.profile.stand["server"], "local")
        self.assertEqual(target.profile.gdb["version"], "15.2")
        self.assertTrue(target.profile.gdb["value_history"])
        self.assertIsNone(target.profile.gdb["stop_details"])

    def test_record_accepts_the_profile(self):
        target = self.module.Target({"checks": []}, TARGET, configuration(),
                                    context=dict(case=CASE, stand=STAND, build=BUILD))
        target.record("run", target.profile)
        data = target.records("run")[0]["data"]
        self.assertEqual(data["case"]["id"], "HW_CI_PROFILE")
        self.assertEqual(data["build"]["defines"], ["STM32F030x8"])

    def test_removed_views_are_gone(self):
        target = self.module.Target({"checks": []}, TARGET, configuration())
        for name in ("settings", "sources", "config", "config_props"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(target, name))
        self.assertEqual(dict(target.profile.case), {})


if __name__ == "__main__":
    unittest.main()
