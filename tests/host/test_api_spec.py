"""Regression for three-component document revisions, using the real checker."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get("CHECK_SPEC"), "requires upstream spec checker")
class ApiSpecRevisionTests(unittest.TestCase):
    def check_document(self, text):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "api.md"
            document.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "ci/check_api_spec.py"),
                 os.environ["CHECK_SPEC"], str(document), "--strict"],
                capture_output=True).returncode

    def test_current_revision(self):
        text = (ROOT / "docs/TECHNICAL_SPECIFICATION_API.md").read_text(encoding="utf-8")
        self.assertEqual(self.check_document(text), 0)

    def test_patch_revision_requires_history(self):
        text = (ROOT / "docs/TECHNICAL_SPECIFICATION_API.md").read_text(encoding="utf-8")
        text = text.replace("| **Ревизия** | 0.1.0", "| **Ревизия** | 0.1.1", 1)
        self.assertNotEqual(self.check_document(text), 0)
