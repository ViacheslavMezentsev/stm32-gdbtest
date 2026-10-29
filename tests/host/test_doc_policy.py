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
        self.link("index.md", "DDTT.md", "API.md", "api/index.md")
        self.link("api/index.md", "read.md")

    def link(self, name, *targets, langs=("ru", "en")):
        for lang in langs:
            page = self.root / "docs" / lang / name
            page.write_text(page.read_text(encoding="utf-8") + "".join(f"[x]({t})\n" for t in targets), encoding="utf-8")

    def pair(self, name):
        import os
        for lang, other in (("ru", "en"), ("en", "ru")):
            p = self.root / "docs" / lang / name
            p.parent.mkdir(parents=True, exist_ok=True)
            link = Path(os.path.relpath(self.root / "docs" / other / name, p.parent)).as_posix()
            p.write_text(f"# Document\n\n[Index](index.md) · [Other]({link})\n", encoding="utf-8")

    def test_optional_russian_only(self):
        (self.root / "docs/ru/new-guide.md").write_text("# Guide", encoding="utf-8")
        self.link("index.md", "new-guide.md", langs=("ru",))
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
        self.link("api/index.md", "nested/method.md")
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

    def test_readme_rules(self):
        live = ("[![Docs](https://img.shields.io/github/actions/workflow/status/o/r/docs.yml)](x)\n"
                "[![Release](https://img.shields.io/github/v/release/o/r)](y)\n\n## A\n\n## B\n")
        for name in ("README.md", "README.en.md"):
            (self.root / name).write_text(live, encoding="utf-8")
        check(self.root)
        stale = live + "[![HW cases](https://img.shields.io/badge/HW%20cases-233-blue)](z)\n"
        (self.root / "README.md").write_text(stale, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "badge"):check(self.root)
        (self.root / "README.md").write_text(live + "\n## C\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "sections"):check(self.root)
        (self.root / "README.md").write_text(live + "line\n" * 120, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "longer"):check(self.root)

    def test_every_page_is_reachable_from_the_map(self):
        (self.root / "docs/ru/orphan.md").write_text("# Orphan", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "orphan.md not linked"):check(self.root)
        (self.root / "docs/ru/orphan.md").write_text("# Сирота: документ перенесён\n\n[Новый адрес](API.md)\n", encoding="utf-8")
        check(self.root)
        self.pair("api/hidden.md")
        with self.assertRaisesRegex(ValueError, "api/hidden.md not reachable"):check(self.root)
