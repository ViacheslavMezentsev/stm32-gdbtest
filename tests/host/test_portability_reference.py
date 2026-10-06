"""Portability P1 reference: server commands, probe identities and tool names stay as before the refactoring.

The reference was taken from the module before the P1 changes. A difference means a behaviour change for an
existing stand; refresh the data file only for an intended change:
python -B tests/host/test_portability_reference.py --refresh
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest import backends, processes, remote  # noqa: E402
from stm32_gdbtest.profile import load_profile  # noqa: E402
from stm32_gdbtest.runner import tool  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "portability_reference.json"
PROFILES = sorted(path.parent.name for path in (ROOT / "tests/firmware/profiles").glob("*/target.toml"))
# Stand values as load_stand() returns them, without looking up executables on this host.
STANDS = {
    "openocd": dict(backend="openocd", serial="ABC123", executable="openocd", speed_khz=1000,
                    flash="if-different", startup_timeout_s=10, remote=None),
    "jlink": dict(backend="jlink", serial="123456789", executable="JLinkGDBServerCLExe", speed_khz=1000,
                  flash="if-different", startup_timeout_s=10, remote=None),
    "stlink": dict(backend="stlink", serial="ABC123", executable="ST-LINK_gdbserver", programmer_dir="/opt/prog",
                   speed_khz=1000, flash="if-different", startup_timeout_s=10, remote=None),
}


def snapshot():
    servers = {}
    for name in PROFILES:
        profile = load_profile(ROOT / "tests/firmware/profiles" / name / "target.toml")
        for backend, stand in STANDS.items():
            try:
                spec = backends.server_spec(stand, 61000, profile, Path("/out"))
                servers[f"{name}/{backend}"] = {key: [str(part).replace("\\", "/") for part in value] if isinstance(value, list)
                                                else value for key, value in spec.items()}
            except ValueError as error:
                servers[f"{name}/{backend}"] = dict(error=str(error))
    return dict(
        servers=servers,
        probe_identity={backend: processes.probe_identity("ABC123" if backend != "jlink" else "123456789", backend)
                        for backend in STANDS},
        remote_check=remote.check_config("id", "openocd"),
        tools={gdb: [tool(gdb, name) for name in ("arm-none-eabi-objdump", "arm-none-eabi-objcopy")]
               for gdb in ("/x/bin/arm-none-eabi-gdb-py3", "C:/x/bin/arm-none-eabi-gdb-py3.exe")})


class PortabilityReferenceTests(unittest.TestCase):
    def test_behaviour_matches_the_reference(self):
        self.assertEqual(json.loads(json.dumps(snapshot())), json.loads(DATA.read_text(encoding="utf-8")))


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        DATA.write_text(json.dumps(snapshot(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        unittest.main()
