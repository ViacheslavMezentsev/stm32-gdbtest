"""Execute the workflow shell with fake tools: a later PASS must not hide a prior FAIL."""
import os
from itertools import product
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
                            '  *doctor*"$FAIL_PROFILE"*) exit "${DOCTOR_EXIT:-0}" ;;\n'
                            '  *run_hw.py*"$FAIL_PROFILE"*|*api040.py*"$FAIL_PROFILE"*) exit "${HW_EXIT:-0}" ;;\n'
                            'esac\nexit 0\n')
            tool.chmod(0o755)
            for profile, suite, (doctor, hardware) in product(
                    ("f103c8", "at32f403a"), ("lifecycle", "api040"), ((0, 0), (1, 0), (0, 1))):
                with self.subTest(profile=profile, suite=suite, doctor=doctor, hardware=hardware):
                    env = dict(os.environ, HOME=str(root), PATH=str(root) + os.pathsep + os.environ["PATH"],
                               PROFILES=f"{profile} f429zi", FAIL_PROFILE=profile, SUITE=suite, STEPS="", GITHUB_RUN_ID="test",
                               GITHUB_RUN_ATTEMPT=f"{doctor}{hardware}", DOCTOR_EXIT=str(doctor), HW_EXIT=str(hardware))
                    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], cwd=root, env=env,
                                            capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, int(bool(doctor or hardware)), result.stderr)
                    self.assertIn(f"{profile}\t{doctor}\t{125 if doctor else hardware}", result.stdout)
                    self.assertIn("f429zi\t0\t0", result.stdout)
                    if doctor or hardware:
                        self.assertIn(f"::error::Profile {profile} failed", result.stdout)
