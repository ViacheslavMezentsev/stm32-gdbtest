"""Publication boundaries must fail even if the private destination exists locally."""
from pathlib import Path
import tempfile
import unittest

from ci.public_docs import check, forbidden_link, is_private, links


PATTERNS = ['docs/research', 'tools/research', 'tests/api-extension', 'tests/**/dev-*']


class PublicDocsTests(unittest.TestCase):
    def test_directory_filters_cover_nested_and_zero_depth(self):
        for path in ('docs/research/a.md', 'tests/dev-a/a.py', 'tests/board/dev-b/test.py'):
            self.assertTrue(is_private(path, PATTERNS), path)
        for path in ('docs/ru/API.md', 'tests/host/test_api.py', 'tests/device/test.py'):
            self.assertFalse(is_private(path, PATTERNS), path)

    def test_relative_encoded_and_remote_links(self):
        page = Path('docs/ru/API.md')
        for target in ('../research/absent.md#section', '../%72esearch/a.md',
                       '../../tests/dev-x/a.py', '/docs/research/a.md',
                       'https://github.com/owner/repo/blob/main/docs/research/a.md',
                       'file:///D:/repo/docs/research/a.md', 'D:/repo/tests/dev-x/a.py'):
            self.assertTrue(forbidden_link(page, target, PATTERNS), target)
        self.assertFalse(forbidden_link(page, '../en/API.md', PATTERNS))

    def test_reference_and_html_links(self):
        text = '[x](../research/a.md)\n[r]: <../research/b.md>\n<a href="../research/c.md">c</a>'
        self.assertEqual(links(text), {'../research/a.md', '../research/b.md', '../research/c.md'})

    def test_plain_policy_text_is_not_a_link(self):
        self.assertEqual(links('Local files use `docs/research/` and `tests/**/dev-*/`.'), set())

    def test_git_free_snapshot_rejects_files_and_missing_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.gitignore').write_text(
                '# BEGIN local development materials\n/docs/research/\n# END local development materials\n')
            (root / 'README.md').write_text('[private](docs/research/missing.md)')
            with self.assertRaisesRegex(ValueError, 'README.md'):
                check(root)
            (root / 'README.md').write_text('Public API')
            check(root)
            private = root / 'docs/research/a.md'
            private.parent.mkdir(parents=True)
            private.write_text('local only')
            with self.assertRaisesRegex(ValueError, 'Published local-only file'):
                check(root)
