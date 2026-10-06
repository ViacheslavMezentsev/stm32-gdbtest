"""Portability P1-3…P1-5: probe settings that used to be fixed — OpenOCD interface and transport, J-Link interface
and device, probe family of the ownership lock. Defaults are covered by test_portability_reference."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest import backends, openocd, probes, processes  # noqa: E402
from stm32_gdbtest.profile import load_profile, validate_profile  # noqa: E402

PROFILE = load_profile(ROOT / "tests/firmware/profiles/f411ce/target.toml")
OPENOCD = dict(backend="openocd", serial="ABC123", executable="openocd", speed_khz=1000, flash="if-different",
               startup_timeout_s=10, remote=None)
JLINK = dict(backend="jlink", serial="123456789", executable="JLinkGDBServerCLExe", speed_khz=1000,
             flash="if-different", startup_timeout_s=10, remote=None)


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

    def test_lock_family_separates_probes_with_the_same_serial(self):
        self.assertNotEqual(processes.probe_identity("ABC123", "openocd", "wlinke"),
                            processes.probe_identity("ABC123", "openocd"))
        with self.assertRaises(ValueError):
            processes.probe_identity("ABC123", "openocd", "Bad Family")


if __name__ == "__main__":
    unittest.main()
