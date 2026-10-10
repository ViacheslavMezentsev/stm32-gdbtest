"""Portability P1-3…P1-5: probe settings that used to be fixed — OpenOCD interface and transport, J-Link interface
and device, probe family of the ownership lock. Defaults are covered by test_portability_reference."""
from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest import backends, openocd, probes, processes  # noqa: E402
from stm32_gdbtest.profile import load_profile, validate_profile  # noqa: E402

PROFILE = load_profile(ROOT / "tests/firmware/profiles/f411ce/target.toml")


def schema1(**overrides):
    """The same profile as schema 1: no backend sections, the reset commands at the top level."""
    data = {key: value for key, value in PROFILE.items() if key not in probes.BACKEND_SECTIONS}
    data.update(schema=1, reset_halt="monitor reset halt", reset_run="monitor reset run")
    data.update(overrides)
    return validate_profile(data)


# Schema 2 keeps the reset commands in a section per GDB server instead of the top level.
SCHEMA2 = {key: value for key, value in PROFILE.items() if key not in ("reset_halt", "reset_run")}
SCHEMA2.update(schema=2, jlink_device="STM32F411CE",
               openocd=dict(reset_halt="monitor reset halt", reset_run="monitor reset run"),
               stlink=dict(reset_halt="monitor reset"), jlink=dict(reset_halt="monitor reset"))
OPENOCD = dict(backend="openocd", serial="ABC123", executable="openocd", speed_khz=1000, flash="if-different",
               startup_timeout_s=10, remote=None)
JLINK = dict(backend="jlink", serial="123456789", executable="JLinkGDBServerCLExe", speed_khz=1000,
             flash="if-different", startup_timeout_s=10, remote=None)
STLINK = dict(backend="stlink", serial="ABC123", executable="ST-LINK_gdbserver", programmer_dir="/opt/prog",
              speed_khz=1000, flash="if-different", startup_timeout_s=10, remote=None)


class ProbeSettingsTests(unittest.TestCase):
    def test_openocd_interface_and_transport(self):
        stand = dict(OPENOCD, interface="interface/wlinke.cfg", transport="sdi")
        command = openocd.server_command(stand, 61000, PROFILE)
        self.assertEqual(command[1:7], ["-f", "interface/wlinke.cfg", "-c", "transport select sdi",
                                        "-f", "target/stm32f4x.cfg"])
        self.assertEqual(probes.family(stand), "wlinke")
        self.assertEqual(probes.family(dict(OPENOCD, interface="interface/stlink-dap.cfg")), "stlink")

    def test_openocd_settings_are_validated(self):
        for key, value in (("interface", "../x.cfg"), ("interface", "interface/a b.cfg"), ("transport", "usb")):
            with self.assertRaises(ValueError):
                openocd.validate(dict(OPENOCD, **{key: value}), local=False)

    def test_jlink_interface_and_profile_device(self):
        profile = validate_profile(dict(PROFILE, mcu="AT32F403ACGU7", jlink_device="AT32F403ACGU7"))
        spec = backends.server_spec(dict(JLINK, interface="JTAG"), 61000, profile, Path("/out"))
        self.assertEqual(spec["command"][1:5], ["-device", "AT32F403ACGU7", "-if", "JTAG"])
        with self.assertRaisesRegex(ValueError, "not validated"):
            backends.server_spec(JLINK, 61000, PROFILE, Path("/out"))

    def test_invalid_jlink_settings(self):
        with self.assertRaises(ValueError):
            validate_profile(dict(PROFILE, jlink_device="bad name"))
        with self.assertRaises(ValueError):
            probes.validate_stand(dict(JLINK, interface="cJTAG"))

    def test_openocd_reset_commands(self):
        # Schema 2 keeps the OpenOCD dialect in its own section.
        profile = validate_profile(dict(SCHEMA2, openocd=dict(reset_halt="monitor reset init",
                                                              reset_run="monitor reset run")))
        self.assertEqual(probes.dialect(profile, "openocd"), ("monitor reset init", ["monitor reset run"]))
        with self.assertRaisesRegex(ValueError, "reset_halt"):
            validate_profile(dict(SCHEMA2, openocd=dict(reset_halt="monitor halt")))
        # Schema 1 accepts the same value at the top level and stays readable.
        self.assertEqual(schema1(reset_halt="monitor reset init")["reset_halt"], "monitor reset init")
        with self.assertRaisesRegex(ValueError, "reset"):
            schema1(reset_halt="monitor halt")

    def test_schema2_sections_replace_the_top_level_reset_keys(self):
        profile = validate_profile(SCHEMA2)
        self.assertEqual(profile["schema"], 2)
        # A schema 2 profile must not carry the old top-level keys.
        with self.assertRaises(ValueError):
            validate_profile(dict(SCHEMA2, reset_halt="monitor reset halt"))
        self.assertEqual(probes.dialect(profile, "openocd"), ("monitor reset halt", ["monitor reset run"]))
        self.assertEqual(probes.dialect(profile, "stlink"), ("monitor reset", []))
        self.assertEqual(probes.dialect(profile, "jlink"), ("monitor reset", []))

    def test_schema2_sections_are_validated(self):
        cases = [
            ("stlink", dict(reset_run="monitor reset run"), "does not use reset_run"),
            ("jlink", dict(reset_run="monitor reset run"), "does not use reset_run"),
            ("openocd", dict(reset_halt="monitor halt"), "Invalid openocd reset_halt"),
            ("openocd", dict(unknown="monitor reset"), "Unknown key in section openocd"),
        ]
        for name, section, message in cases:
            with self.subTest(section=name, value=section), self.assertRaisesRegex(ValueError, message):
                validate_profile(dict(SCHEMA2, **{name: section}))
        with self.assertRaisesRegex(ValueError, "must be a table"):
            validate_profile(dict(SCHEMA2, stlink="monitor reset"))

    def test_schema2_without_a_section_uses_the_builtin_dialect(self):
        profile = validate_profile({key: value for key, value in SCHEMA2.items()
                                    if key not in ("openocd", "jlink", "stlink")})
        self.assertEqual(probes.dialect(profile, "stlink"), ("monitor reset", []))
        # The ST server refuses the OpenOCD-only command, so the default must not be the OpenOCD one.
        self.assertNotIn("monitor reset halt", probes.dialect(profile, "stlink"))

    def test_session_override_wins_over_the_section(self):
        # ТЗ API 6.6: the override is the first step of the documented precedence, applied when the run
        # is prepared, so the session records the value every consumer will use.
        profile = validate_profile(SCHEMA2)
        with patch.dict(os.environ, {"STM32_GDBTEST_RESET_COMMAND": "monitor halt"}):
            self.assertEqual(probes.dialect(profile, "openocd")[0], "monitor halt")
            self.assertEqual(probes.dialect(profile, "stlink")[0], "monitor halt")
            spec = backends.server_spec(OPENOCD, 61000, profile, Path("/out"))
            self.assertEqual(spec["reset_halt"], "monitor halt")

    def test_server_spec_takes_the_reset_command_from_the_backend_section(self):
        profile = validate_profile(SCHEMA2)
        for stand, expected in ((OPENOCD, "monitor reset halt"), (STLINK, "monitor reset"), (JLINK, "monitor reset")):
            with self.subTest(backend=stand["backend"]):
                spec = backends.server_spec(stand, 61000, profile, Path("/out"))
                self.assertEqual(spec["reset_halt"], expected)
        # Schema 1 still works for the stands delivered with it.
        spec = backends.server_spec(OPENOCD, 61000, schema1(), Path("/out"))
        self.assertEqual(spec["reset_halt"], "monitor reset halt")
        self.assertEqual(spec["finish"], ["monitor reset run", "disconnect"])

    def test_stlink_and_jlink_finish_with_their_own_commands(self):
        profile = validate_profile(SCHEMA2)
        stlink = backends.server_spec(STLINK, 61000, profile, Path("/out"))
        jlink = backends.server_spec(dict(JLINK, interface="SWD"), 61000, profile, Path("/out"))
        self.assertEqual(stlink["finish"], ["monitor reset", "detach"])
        self.assertEqual(jlink["finish"], ["monitor reset", "monitor go", "disconnect"])

    def test_lock_family_separates_probes_with_the_same_serial(self):
        self.assertNotEqual(processes.probe_identity("ABC123", "openocd", "wlinke"),
                            processes.probe_identity("ABC123", "openocd"))
        with self.assertRaises(ValueError):
            processes.probe_identity("ABC123", "openocd", "Bad Family")


if __name__ == "__main__":
    unittest.main()
