"""Required API translations cannot be bypassed by adding optional Russian docs."""
import tempfile
import unittest
from pathlib import Path
from ci.doc_policy import check, ROOT_PAIRS, LOCALIZED


class DocumentationPolicyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for pair in ROOT_PAIRS:
            for name in pair:
                (self.root / name).write_text("# Root", encoding="utf-8")
        for name in (*LOCALIZED, "api/index.md", "api/read.md"):
            self.pair(name)

    def pair(self, name):
        import os
        for lang, other in (("ru", "en"), ("en", "ru")):
            p = self.root / "docs" / lang / name
            p.parent.mkdir(parents=True, exist_ok=True)
            link = Path(os.path.relpath(self.root / "docs" / other / name, p.parent)).as_posix()
            p.write_text(f"# Document\n\n[Index](index.md) · [Other]({link})\n", encoding="utf-8")

    def test_optional_russian_only(self):
        (self.root / "docs/ru/new-guide.md").write_text("# Guide", encoding="utf-8")
        check(self.root)

    def test_every_required_page(self):
        for name in LOCALIZED:
            with self.subTest(name=name):
                p = self.root / "docs/en" / name
                content = p.read_bytes();p.unlink()
                with self.assertRaises(ValueError):check(self.root)
                p.write_bytes(content)

    def test_nested_api_and_orphan_english(self):
        self.pair("api/nested/method.md")
        check(self.root)
        (self.root / "docs/ru/api/nested/method.md").unlink()
        with self.assertRaises(ValueError):check(self.root)

    def test_missing_api_translation(self):
        (self.root / "docs/en/api/read.md").unlink()
        with self.assertRaises(ValueError):check(self.root)

    def test_navigation(self):
        (self.root / "docs/en/api/read.md").write_text("# Missing navigation", encoding="utf-8")
        with self.assertRaises(ValueError):check(self.root)

    def test_root_translation(self):
        (self.root / "README.en.md").unlink()
        with self.assertRaises(ValueError):check(self.root)
