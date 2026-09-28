"""Remote GDB server over SSH without an SSH server or a debugger (TC-99…TC-102)."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from stm32_gdbtest import remote
from stm32_gdbtest.backends import load_stand
from stm32_gdbtest.processes import probe_identity

ROOT = Path(__file__).resolve().parents[2]
FAKE_SERVER = """
import socket, sys, time
port = int(sys.argv[sys.argv.index("-port") + 1])
open(sys.argv[sys.argv.index("-log") + 1], "w").write("fake server log\\n")
s = socket.socket(); s.bind(("127.0.0.1", port)); s.listen(1)
print("Waiting for GDB connection...", flush=True)
time.sleep(60)
"""


class RemoteSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.key = Path(self.temp.name) / "id_ed25519"
        self.key.write_text("key")

    def test_remote_table_rejects_passwords_and_unsafe_values(self):
        # TC-99: ТЗ 5.18.1
        with patch("stm32_gdbtest.remote.shutil.which", return_value="/usr/bin/ssh"):
            good = remote.load(dict(host="orangepi5", user="orangepi", identity_file=str(self.key),
                                    env_script="~/.local/stm32-gdbtest/env.sh"))
            self.assertEqual((good["port"], good["ssh"]), (22, "/usr/bin/ssh"))
            self.assertIsNone(remote.load(None))
            for table, message in ((dict(host="h", password="x"), "Passwords"),
                                   (dict(host="h", passphrase="x"), "Passwords"),
                                   (dict(host="h", proxy="x"), "Unknown remote setting"),
                                   (dict(host="-oProxyCommand=x"), "host"),
                                   (dict(host="a b"), "host"),
                                   (dict(host="h", user="root;id"), "user"),
                                   (dict(host="h", port=0), "port"),
                                   (dict(host="h", identity_file="relative/key"), "identity_file"),
                                   (dict(host="h", env_script="env.sh; reboot"), "env_script")):
                with self.assertRaisesRegex(ValueError, message):
                    remote.load(table)
        with patch("stm32_gdbtest.remote.shutil.which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "SSH client"):
                remote.load(dict(host="h"))

    def test_ssh_command_is_key_only_and_script_is_quoting_free(self):
        # TC-100: ТЗ 5.18.1, 5.18.2
        with patch("stm32_gdbtest.remote.shutil.which", return_value="ssh"):
            settings = remote.load(dict(host="orangepi5", user="orangepi", port=2200, identity_file=str(self.key)))
        command = remote.ssh_command(settings, "-L", "127.0.0.1:1:127.0.0.1:2")
        for option in ("BatchMode=yes", "StrictHostKeyChecking=yes", "IdentitiesOnly=yes"):
            self.assertIn(option, command)
        self.assertEqual(command[-1], "orangepi5")
        self.assertEqual(command[command.index("-p") + 1], "2200")
        config = remote.serve_config("ab", 45000, ["openocd", "-c", "gdb_port {port}", "it's"])
        script = remote.remote_script(settings, config)
        self.assertIn('"$HOME"/.local/stm32-gdbtest/env.sh', script)
        parts = script.split("exec python3 -c 'import base64,sys;exec(base64.b64decode(sys.argv[1]))' ")[1].split()
        self.assertEqual(base64.b64decode(parts[0]), remote.HELPER.read_bytes())
        self.assertEqual(json.loads(base64.b64decode(parts[1])), config)
        self.assertNotIn("it's", script)

    def test_remote_stand_resolves_tools_on_the_stand_host(self):
        # TC-102: ТЗ 5.18.1, 6.10.3
        path = Path(self.temp.name) / "stand.toml"
        # Only the SSH client exists on this computer; the servers are on the stand host.
        with patch("shutil.which", side_effect=lambda name: "ssh" if name == "ssh" else None):
            path.write_text('[probe]\nbackend="jlink"\nserial="69653773"\n[remote]\nhost="orangepi5"\n')
            stand = load_stand(path)
            self.assertEqual(stand["executable"], "JLinkGDBServerCLExe")
            self.assertEqual(stand["remote"]["host"], "orangepi5")
            path.write_text('[probe]\nbackend="openocd"\nserial="066C"\nexecutable="/opt/x/openocd"\n'
                            '[remote]\nhost="orangepi5"\n')
            self.assertEqual(load_stand(path)["executable"], "/opt/x/openocd")
            path.write_text('[probe]\nbackend="stlink"\nserial="066C"\nprogrammer_dir="C:/ST"\n'
                            '[remote]\nhost="x86stand"\n')
            with self.assertRaisesRegex(ValueError, "stand host"):
                load_stand(path)
            path.write_text('[probe]\nbackend="openocd"\nserial="066C"\n')
            with self.assertRaisesRegex(FileNotFoundError, "OpenOCD"):
                load_stand(path)


@unittest.skipIf(os.name == "nt", "the stand host is Linux")
class RemoteHelperTests(unittest.TestCase):
    """TC-101: ТЗ 5.18.3–5.18.5 — the helper exactly as the stand host runs it, without SSH."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.env = dict(os.environ, STM32_GDBTEST_LOCK_DIR=str(self.dir / "locks"))
        server = self.dir / "fake_server.py"
        server.write_text(FAKE_SERVER)
        self.identity = probe_identity("123456", "jlink")
        self.command = [sys.executable, str(server), "-port", "{port}", "-log", "{dir}/jlink.log"]
        self.lock = self.dir / "locks/stm32-gdbtest-locks" / f"probe.v1.{self.identity}.lock"

    def start(self, port, command=None):
        settings = dict(host="h", user=None, port=22, identity_file=None, env_script=None, ssh="ssh")
        script = remote.remote_script(settings, remote.serve_config(self.identity, port, command or self.command))
        return subprocess.Popen(["sh", "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                env=self.env, text=True)

    def wait_for(self, process, marker):
        lines = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            line = process.stdout.readline()
            if not line:
                break
            lines.append(line)
            if marker in line:
                return lines
        self.fail("marker not seen: " + "".join(lines))

    def test_serve_locks_streams_stops_on_eof_and_unlocks(self):
        owner = self.start(47311)
        self.addCleanup(lambda: owner.poll() is None and owner.kill())
        lines = self.wait_for(owner, "Waiting for GDB connection")
        self.assertIn("STM32_GDBTEST_REMOTE ready-to-start port=47311", "".join(lines))
        self.assertTrue(self.lock.read_text().startswith("pid="))
        second = self.start(47312)
        output = second.communicate(timeout=20)[0]
        self.assertIn("error=busy", output)
        self.assertEqual(second.returncode, 3)
        owner.stdin.close()
        rest = owner.stdout.read()
        owner.wait(timeout=20)
        self.assertIn("STM32_GDBTEST_REMOTE log=jlink.log\nfake server log", rest)
        self.assertIn("STM32_GDBTEST_REMOTE exit=", rest)
        self.assertEqual(self.lock.read_text(), "")
        workdir = "".join(lines).split(" dir=")[1].split()[0]
        self.assertFalse(Path(workdir).exists())

    def test_abandoned_record_and_missing_server_are_refused(self):
        self.lock.parent.mkdir(parents=True)
        self.lock.write_text("pid=1 remote\n")
        output = self.start(47313).communicate(timeout=20)[0]
        self.assertIn("error=abandoned Abandoned debugger ownership", output)
        self.assertEqual(self.lock.read_text(), "")
        output = self.start(47314, ["no-such-gdb-server"]).communicate(timeout=20)[0]
        self.assertIn("error=executable", output)
        self.assertEqual(self.lock.read_text(), "")


if __name__ == "__main__":
    unittest.main()
