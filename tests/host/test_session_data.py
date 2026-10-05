"""Project data files of session.toml ([data]) and the build summary seen by scenarios."""
from pathlib import Path
import tempfile
import unittest

from stm32_gdbtest.build_manifest import summary
from stm32_gdbtest.config_transport import dumps, loads
from stm32_gdbtest.configuration import ConfigError, load_session

from test_session_config import TARGET


class SessionDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "target.toml").write_text(TARGET, encoding="utf-8")
        (self.root / "board.toml").write_text('[board]\nname = "NUCLEO-F411RE"\nhse_hz = 8_000_000\n',
                                              encoding="utf-8")

    def session(self, data='[data]\nboard = "board.toml"\n'):
        path = self.root / "session.toml"
        path.write_text('[config]\ntarget = "target.toml"\n' + data, encoding="utf-8")
        return path

    def test_data_files_are_captured_with_their_digest(self):
        snapshot = load_session(self.session(), environ={})
        self.assertEqual(snapshot.config["data"]["board"]["board"]["hse_hz"], 8000000)
        self.assertEqual(snapshot.config_props["data.board"]["reference"], "board.toml")
        self.assertEqual(len(snapshot.config_props["data.board"]["sha256"]), 64)
        self.assertEqual(dict(load_session(self.session(""), environ={}).config["data"]), {})

    def test_invalid_declarations_fail_before_the_run(self):
        for data, code in (('[data]\nBoard = "board.toml"\n', "data"),
                           ('[data]\nboard = ""\n', "reference"),
                           ('[data]\nboard = "absent.toml"\n', "source"),
                           ('data = "board.toml"\n', "session"),
                           ('[other]\nx = 1\n', "session")):
            with self.subTest(data=data), self.assertRaises(ConfigError) as caught:
                load_session(self.session(data), environ={})
            self.assertEqual(caught.exception.code, code)

    def test_capsule_carries_data_files_without_the_sources(self):
        capsule = dumps(load_session(self.session(), environ={}))
        (self.root / "board.toml").unlink()
        received = loads(capsule)
        self.assertEqual(received.config["data"]["board"]["board"]["name"], "NUCLEO-F411RE")

    def test_build_summary_keeps_versions_and_defines_only(self):
        manifest = dict(
            compilers=[dict(name="arm-none-eabi-gcc.exe", sha256="x" * 64, version="13.3.1")],
            cube_packages=["STM32Cube_FW_F4_V1.28.0"],
            units=[dict(source="Core/Src/main.c", flags=["-DUSE_HAL_DRIVER", "-DSTM32F411xE", "-O2"]),
                   dict(source="Drivers/x.c", flags=["-DUSE_HAL_DRIVER"])],
            library_versions=[dict(file="a.h", sha256="y", macros={
                "__STM32F4xx_HAL_VERSION_MAIN": 1, "__STM32F4xx_HAL_VERSION_SUB1": 8,
                "__STM32F4xx_HAL_VERSION_SUB2": 3, "__STM32F4xx_HAL_VERSION_RC": 0,
                "__CM4_CMSIS_VERSION_MAIN": 5, "__CM4_CMSIS_VERSION_SUB": 6})])
        result = summary(manifest)
        self.assertEqual(result["libraries"], {"CM4_CMSIS": "5.6", "STM32F4xx_HAL": "1.8.3"})
        self.assertEqual(result["defines"], ["STM32F411xE", "USE_HAL_DRIVER"])
        self.assertEqual(result["compilers"], [dict(name="arm-none-eabi-gcc", version="13.3.1")])
        self.assertEqual(result["cube_packages"], ["STM32Cube_FW_F4_V1.28.0"])
        self.assertEqual(result["sources"], ["Core/Src/main.c", "Drivers/x.c"])


if __name__ == "__main__":
    unittest.main()
