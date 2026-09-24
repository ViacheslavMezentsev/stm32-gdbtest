"""Real process tests; use synthetic identities and never start a debug server."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from stm32_gdbtest.processes import probe_lock, probe_mutex_name, _kernel_api

ROOT = Path(__file__).resolve().parents[2]
OWNER = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from stm32_gdbtest.processes import probe_lock
with probe_lock(Path(sys.argv[2]), sys.argv[3], 'openocd'):
    Path(sys.argv[4]).write_text('ready')
    time.sleep(30)
"""


@unittest.skipUnless(os.name == "nt", "Windows mutex")
class ProbeLockTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "build/lock-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.serial = "TEST" + uuid.uuid4().hex

    def owner(self):
        # The holder imports an independent copy, not this process's module object.
        module = self.root / "module copy"
        shutil.copytree(ROOT / "stm32_gdbtest", module / "stm32_gdbtest", ignore=shutil.ignore_patterns("__pycache__"))
        ready = self.root / "ready"
        process = subprocess.Popen([sys.executable, "-B", "-c", OWNER, str(module),
            str(self.root / "project A"), self.serial, str(ready)], cwd=self.root,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 5
        while not ready.exists():
            if process.poll() is not None:
                self.fail(process.communicate(timeout=5)[1])
            if time.monotonic() >= deadline:
                self.fail("Owner did not acquire lock in time")
            time.sleep(0.02)
        return process

    def test_cross_project_cross_backend_and_independent_devices(self):
        owner = self.owner()
        for backend in ("openocd", "stlink"):
            with self.assertRaisesRegex(RuntimeError, "another runner"):
                with probe_lock(self.root / "project B", self.serial.lower(), backend):
                    self.fail("Second owner entered")
        self.assertFalse((self.root / "project B").exists())
        from stm32_gdbtest.runner import run
        session = dict(root=str(self.root), out=str(self.root / "reports"),
                       stand="mock.toml", profile="mock-profile.toml")
        with patch("stm32_gdbtest.runner.load_stand", return_value=dict(backend="stlink", serial=self.serial)), \
                patch("stm32_gdbtest.runner.load_profile", return_value={}), \
                patch("stm32_gdbtest.runner.execute") as execute:
            self.assertEqual(run(session, dict(id="HW_LOCKED", timeout_s=10)), 2)
            execute.assert_not_called()
        report = json.loads(next((self.root / "reports").glob("*/result.json")).read_text())
        self.assertIn("another runner", report["error"])
        self.assertNotIn("connection_attempted", report)

        with probe_lock(self.root / "project C", self.serial + "2", "stlink"):
            pass
        with probe_lock(self.root / "project D", self.serial, "jlink"):
            pass
        owner.kill()
        owner.wait(timeout=5)
        with probe_lock(self.root / "project B", self.serial, "stlink"):
            pass

    def test_exception_and_nested_use_release(self):
        with self.assertRaisesRegex(ValueError, "injected"):
            with probe_lock(self.root, self.serial):
                with self.assertRaisesRegex(RuntimeError, "this process"):
                    with probe_lock(self.root / "other", self.serial, "stlink"):
                        self.fail("Recursive ownership")
                raise ValueError("injected")
        with probe_lock(self.root, self.serial):
            pass

    def test_abandoned_mutex_fails_closed(self):
        owner = self.owner()
        api = _kernel_api()
        handle = api.CreateMutexW(None, False, probe_mutex_name(self.serial))
        self.assertTrue(handle)
        try:
            # Keep the kernel object alive while its owner dies, exercising WAIT_ABANDONED.
            owner.kill()
            owner.wait(timeout=5)
            with self.assertRaisesRegex(RuntimeError, "Abandoned"):
                with probe_lock(self.root / "other", self.serial):
                    self.fail("Abandoned owner silently accepted")
            self.assertFalse((self.root / "other").exists())
            # Synthetic owner had no children; retry is safe here, not generally after a HW crash.
            with probe_lock(self.root / "other", self.serial):
                pass
        finally:
            self.assertTrue(api.CloseHandle(handle))

    def test_identity_mapping_and_validation(self):
        self.assertEqual(probe_mutex_name("aB12", "openocd"), probe_mutex_name("AB12", "stlink"))
        self.assertNotEqual(probe_mutex_name("1234", "jlink"), probe_mutex_name("1234", "stlink"))
        for serial, backend in (("", "stlink"), ("a/b", "openocd"), ("AB", "unknown")):
            with self.assertRaises(ValueError):
                probe_mutex_name(serial, backend)
