"""The shared run-profile scenario accepts every backend the module supports.

`HW_CI_PROFILE` reads the stand section of the run profile, so its list of accepted backends must stay in
step with `stm32_gdbtest.backends`. The ST-LINK GDB Server stand found the gap: `stlink` was rejected by
the scenario while the module supports it.
"""
import importlib.util
from pathlib import Path
import unittest

from stm32_gdbtest.matchers import Matcher

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "tests/firmware/common/tests/board/test_profile.py"

TARGET = dict(mcu="STM32F030R8", flash_start=0x08000000, flash_size=65536, flash_size_address=0x1FFF7A22,
              identity=dict(address=0x40015800, mask=0xFFF, value=0x440))
BOARD = dict(board=dict(name="NUCLEO-F030R8", led="PA5"))
BUILD = dict(compilers=[dict(name="arm-none-eabi-gcc", version="13.3.1")],
             libraries=["STM32Cube_FW_F0 CMSIS"], defines=["STM32F030x8"], sources=["src/app.c"])
OPTIONS = {"api.records.max_records": 32, "api.reset.command": "monitor reset halt"}


class Checked(Exception):
    """Raised by the fake target when a check does not hold."""


class Mapping(dict):
    """A read-only section of the run profile, like the one the module freezes."""

    def __setitem__(self, key, value):
        raise TypeError("read-only")


class Profile(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    # The scenario reads effective values through the dotted form of the profile.
    def get(self, key, default=None):
        return OPTIONS.get(key, default)


class Target:
    def __init__(self, backend, reset_command="monitor reset halt"):
        self.profile = Profile(
            identity=Mapping(TARGET["identity"]),
            mcu=TARGET["mcu"],
            flash_size=TARGET["flash_size"],
            flash_size_address=TARGET["flash_size_address"],
            flash_start=TARGET["flash_start"],
            case=Mapping(id="HW_CI_PROFILE", function="run_profile", timeout_s=45, contracts=("ci_app_api",)),
            stand=Mapping(backend=backend, server="local", speed_khz=1000, reset_command=reset_command),
            files=Mapping(target=Mapping(sha256="a" * 64, reference="target.toml")),
            data=Mapping(board=Mapping(board=Mapping(BOARD["board"]))),
            build=Mapping(compilers=[dict(name="arm-none-eabi-gcc", version="13.3.1")],
                          libraries=["STM32Cube_FW_F0 CMSIS"], defines=["STM32F030x8"]),
            gdb=Mapping(version="14.2.90", stop_details=None),
            api=Mapping(records=Mapping(max_records=32), reset=Mapping(command="monitor reset halt")),
            origin=self.origin,
        )
        self.checks = []

    # The scenario asks which captured file provided a value.
    def origin(self, key):
        return dict(state="file", file="board.toml" if "board" in key else "target.toml")

    def evaluate(self, expression, **options):
        # The scenario reads the chip identity and the flash size register.
        if "40015800" in expression:
            return TARGET["identity"]["value"]
        return TARGET["flash_size"] // 1024

    def memory(self, address, size):
        return (0x20000000).to_bytes(4, "little") + (TARGET["flash_start"] | 1).to_bytes(4, "little")

    def check(self, name, actual, expected=True):
        if isinstance(expected, Matcher):
            passed = expected.matches(actual)
        elif expected is True:
            passed = bool(actual)
        elif isinstance(expected, dict) and "in" in expected:
            passed = actual in expected["in"]
        else:
            passed = actual == expected
        self.checks.append(name)
        if not passed:
            raise Checked(name)

    def reach(self, location, **options):
        # The real target learns the stop details at the first stop. The published section refuses
        # assignment from a scenario, so the run itself writes it through the mapping.
        dict.__setitem__(self.profile["gdb"], "stop_details", False)

    def record(self, name, data):
        return None


class ProfileScenarioTests(unittest.TestCase):
    def scenario(self):
        spec = importlib.util.spec_from_file_location("profile_scenario", SCENARIO)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.run_profile

    def test_every_supported_backend_passes_the_stand_section(self):
        scenario = self.scenario()
        for backend in ("openocd", "stlink", "st-util", "jlink"):
            with self.subTest(backend=backend):
                target = Target(backend)
                scenario(target)
                self.assertIn("stand backend", target.checks)

    def test_the_reset_command_comes_from_the_run_profile(self):
        # ТЗ API 6.6: the run resolves the command from the backend dialect and publishes it in the stand
        # section; the scenario no longer reads the removed `api.toml` key `reset.command`.
        scenario = self.scenario()
        for command in ("monitor reset", "monitor reset halt", "monitor reset init"):
            with self.subTest(command=command):
                target = Target("stlink", reset_command=command)
                scenario(target)
                self.assertIn("reset command", target.checks)
        with self.assertRaises(Checked) as caught:
            scenario(Target("stlink", reset_command="reset halt"))
        self.assertEqual(str(caught.exception), "reset command")

    def test_unknown_backend_is_rejected(self):
        scenario = self.scenario()
        with self.assertRaises(Checked) as caught:
            scenario(Target("unknown"))
        self.assertEqual(str(caught.exception), "stand backend")


if __name__ == "__main__":
    unittest.main()
