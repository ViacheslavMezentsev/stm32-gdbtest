"""Execute the workflow shell with fake tools: a later PASS must not hide a prior FAIL."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "workflow shell requires Linux bash")
class HardwareWorkflowTests(unittest.TestCase):
    def test_campaign_exit_and_per_profile_diagnostics(self):
        workflow = (ROOT / ".github/workflows/hardware.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Doctor and hardware runs of the prepared packages\n", 1)[1]
        block = block.split("        run: |\n", 1)[1].split("      - name: Keep results", 1)[0]
        script = "\n".join(line[10:] for line in block.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = root / ".local/stm32-gdbtest/env.sh"
            environment.parent.mkdir(parents=True)
            environment.write_text("# isolated test environment\n")
            tool = root / "python3"
            tool.write_text('#!/bin/sh\ncase "$*" in\n'
                            '  *doctor*f103c8*) exit "${DOCTOR_EXIT:-0}" ;;\n'
                            '  *run_hw.py*f103c8*) exit "${HW_EXIT:-0}" ;;\n'
                            'esac\nexit 0\n')
            tool.chmod(0o755)
            for doctor, hardware in ((0, 0), (1, 0), (0, 1)):
                with self.subTest(doctor=doctor, hardware=hardware):
                    env = dict(os.environ, HOME=str(root), PATH=str(root) + os.pathsep + os.environ["PATH"],
                               PROFILES="f103c8 f429zi", STEPS="", GITHUB_RUN_ID="test",
                               GITHUB_RUN_ATTEMPT=f"{doctor}{hardware}", DOCTOR_EXIT=str(doctor), HW_EXIT=str(hardware))
                    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], cwd=root, env=env,
                                            capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, int(bool(doctor or hardware)), result.stderr)
                    self.assertIn(f"f103c8\t{doctor}\t{hardware}", result.stdout)
                    self.assertIn("f429zi\t0\t0", result.stdout)
                    if doctor or hardware:
                        self.assertIn("::error::Profile f103c8 failed", result.stdout)
