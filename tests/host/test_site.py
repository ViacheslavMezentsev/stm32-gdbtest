"""GitHub Pages site: content consistency with the API reference, links, anchors and a deterministic build."""
import ast
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ci.build_site import ROOT, build, content


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links, self.ids, self.lang, self.h1, self.scripts = [], [], None, 0, []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = a.get('lang')
        if tag == 'h1':
            self.h1 += 1
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'script':
            self.scripts.append(a.get('src', ''))
        for key in ('href', 'src'):
            if key in a:
                self.links.append(a[key])


class SiteContentTests(unittest.TestCase):
    def test_groups_reference_existing_cards(self):
        cards = {p.stem for p in (ROOT / 'docs/ru/api').glob('*.md')} - {'index'}
        removed = {name for name, _ in content.REMOVED}
        self.assertEqual(set(content.CARDS), cards - removed)
        grouped = [card for group in content.API for card in group['cards']]
        self.assertEqual(sorted(grouped), sorted(set(grouped)))
        self.assertEqual(set(grouped), set(content.CARDS))
        for name in cards:
            self.assertTrue((ROOT / 'docs/en/api' / f'{name}.md').is_file(), name)

    def test_cards_state_the_same_first_release(self):
        for card, (_, since, _, _) in content.CARDS.items():
            first = since.rstrip('¹')
            for lang, label in (('ru', '**Доступен с:** '), ('en', '**Available since:** ')):
                text = (ROOT / 'docs' / lang / 'api' / f'{card}.md').read_text(encoding='utf-8')
                found = re.search(re.escape(label) + r'(\S+?)[;\s]', text)
                self.assertIsNotNone(found, f'{lang}/{card}')
                self.assertEqual(found.group(1), first, f'{lang}/{card}')
                self.assertNotRegex(text, r'(?i)кандидат 0\.5\.0|0\.5\.0 candidate|\| (Свойство|Property) \|')

    def test_localized_content_is_complete(self):
        for group in content.API:
            self.assertEqual(set(group['ru']), set(group['en']))
            self.assertTrue(all(group['ru'].values()) and all(group['en'].values()), group['id'])
        for route in content.ROUTES:
            self.assertTrue(set(route['nodes']) | set(route.get('alt', ())) <= set(content.SKILLS), route['id'])
        for row in content.WITNESSES:
            self.assertTrue(set(row[3]) <= set(content.SKILLS))
        self.assertTrue({row[0] for row in content.CHOOSE} <= set(content.SKILLS))
        self.assertEqual(len(content.RULES['ru']), len(content.RULES['en']))

    def test_fragments_are_valid_python(self):
        flags = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
        for group in content.API:
            for kind in ('good', 'bad'):
                compile(group[kind], f'{group["id"]}:{kind}', 'exec', flags=flags)


class SiteBuildTests(unittest.TestCase):
    def test_build_links_and_determinism(self):
        with tempfile.TemporaryDirectory(prefix='stm32-gdbtest-pages-') as temp:
            output = build(Path(temp))
            docs = {p: Document(p.read_text(encoding='utf-8')) for p in output.rglob('*.html')}
            self.assertEqual(len(docs), 2 * (3 + len(content.API)))
            for path, doc in docs.items():
                self.assertEqual(doc.h1, 1, str(path))
                self.assertEqual(doc.lang, 'en' if path.name == 'index.en.html' else 'ru', str(path))
                self.assertEqual(len(doc.ids), len(set(doc.ids)), str(path))
                self.assertTrue(all(not urlsplit(src).scheme for src in doc.scripts), str(path))
                for link in doc.links:
                    url = urlsplit(link)
                    if url.scheme:
                        self.assertEqual(url.scheme, 'https', link)
                        continue
                    self.assertFalse(url.netloc)
                    target = (path.parent / unquote(url.path)).resolve() if url.path else path
                    self.assertTrue(target.is_relative_to(output.resolve()), link)
                    self.assertTrue(target.exists(), f'{path}: missing {link}')
                    if url.fragment:
                        self.assertIn(unquote(url.fragment), docs[target].ids, f'{path}: {link}')
            before = {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
            build(output)
            after = {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
            self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
