"""Campaign summary semantics, HTML escaping and complete publication (ТЗ 5.23)."""
import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from stm32_gdbtest.results import Limits, pipeline
from stm32_gdbtest import result_index, result_report


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.attrs = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)


class ReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        selection = dict(schema=1, campaign_id='campaign', name='Bring-up', runs=[])
        for number, (status, mode) in enumerate([('FAIL', 'hardware'), ('PASS', 'hardware'),
                                                ('ERROR', 'hardware'), ('SKIP', 'hardware'),
                                                ('alien', 'hardware'), ('PASS', 'prepare')]):
            data = dict(id='SAME_CASE', run_id=str(number), status=status, mode=mode,
                        command_code=2 if number in (1, 2) else 0,
                        skip_reason='channel unavailable' if number == 3 else None)
            if number == 1:
                data['capture'] = dict(status='error', completion='normal', error=dict(message='disk'))
            relative = str(number) + '.json'
            (self.root / relative).write_text(json.dumps(data))
            selection['runs'].append(dict(result=relative, stand='bench'))
        self.index = result_index.build(self.root, selection)

    def render(self, name='output', **kwargs):
        output = self.root / name
        code = result_report.report(self.root, self.index, output, Limits(), **kwargs)
        data = json.loads((output / 'campaign.json').read_text(encoding='utf-8'))
        html = (output / 'campaign.html').read_text(encoding='utf-8')
        return code, data, html

    def test_independent_outcomes_and_attempts(self):
        code, data, html = self.render()
        self.assertEqual(code, 2)  # Unknown input verdict is diagnosed by the index.
        self.assertIsNone(data['aggregate_verdict'])
        self.assertEqual(len(data['runs']), 6)
        self.assertEqual(data['counts']['hardware']['verdicts'], dict(PASS=1, FAIL=1, ERROR=1, SKIP=1, UNKNOWN=1))
        self.assertEqual(data['counts']['prepare']['total'], 1)
        self.assertEqual(data['runs'][1]['verdict'], 'PASS')
        self.assertEqual(data['runs'][1]['command_code'], 2)
        self.assertEqual(data['runs'][1]['integrity'], 'ok')
        self.assertEqual(data['runs'][1]['capture']['status'], 'error')
        self.assertEqual(data['runs'][4]['original_verdict'], 'alien')
        self.assertIn('channel unavailable', html)

    def test_fresh_integrity(self):
        (self.root / '0.json').write_text('changed')
        (self.root / '1.json').unlink()
        _, data, _ = self.render()
        self.assertEqual(data['runs'][0]['current_artifacts'][0]['state'], 'changed')
        self.assertEqual(data['runs'][1]['current_artifacts'][0]['state'], 'missing')
        self.assertEqual(data['runs'][1]['verdict'], 'PASS')
        self.assertEqual(data['runs'][1]['integrity'], 'issues')

    def test_html_injection_and_themes(self):
        payload = '</pre><script>alert(1)</script><img src=x onerror=alert(2)>'
        self.index['name'] = payload
        self.index['runs'][0]['stand'] = payload
        self.index['runs'][0]['diagnostics'] = [payload]
        for theme in ('auto', 'light', 'dark'):
            _, _, html = self.render(theme, theme=theme)
            elements = Elements(html)
            self.assertEqual(elements.tags.count('script'), 1)
            from stm32_gdbtest.report_style import SCRIPT
            self.assertEqual(html.split('<script>')[1].split('</script>')[0], SCRIPT)
            self.assertNotIn('img', elements.tags)
            self.assertFalse(any(key in ('href', 'src', 'onerror') for key, _ in elements.attrs))
            self.assertIn(('data-theme', theme), elements.attrs)
            self.assertIn('&lt;script&gt;', html)
            self.assertEqual(elements.tags.count('details'), 6)

    def test_view_controls_preserve_all_evidence(self):
        _, data, html = self.render()
        elements = Elements(html)
        self.assertEqual(elements.tags.count('button'), 5)
        self.assertIn(('data-view-choice', 'normal'), elements.attrs)
        self.assertIn(('data-view-choice', 'expert'), elements.attrs)
        self.assertIn('noscript', elements.tags)
        self.assertNotIn(('data-view', 'normal'), elements.attrs)  # Full fallback without JS.
        self.assertEqual(elements.tags.count('details'), len(data['runs']))
        self.assertIn('<td>error<small class="expert">', html)  # Error visible in both views.
        self.assertIn('<td class="expert"><details>', html)
        self.assertIn('<td class="PASS">PASS</td><td>2</td>', html)

    def test_output_limit_and_duplicate_ids(self):
        output = self.root / 'output'
        with self.assertRaises(ValueError):
            result_report.report(self.root, self.index, output, Limits(output_bytes=100))
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob('.report-*')))
        self.assertFalse(list(self.root.glob('*.lock')))
        self.index['runs'][1]['run_id'] = '0'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.render()

    def test_export_fingerprints_and_selection(self):
        exported = dict(schema=1, sources=[], records=[], measurements=[], definitions=[], diagnostics=[],
                        command_code=0, selection_indices=[0, 1, 2, 3, 4])
        source = dict(source_index=0, run_id='0', case_id='SAME_CASE',
                      result_sha256=self.index['runs'][0]['artifacts'][0]['sha256'], records_sha256='0' * 64)
        exported['sources'] = [source]
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.render(exported=exported)
        self.assertFalse((self.root / 'output').exists())
        exported['sources'] = []
        exported['selection_indices'] = [0, 1]
        with self.assertRaisesRegex(ValueError, 'selection'):
            self.render(exported=exported)

    def test_large_report_keeps_all_rows(self):
        self.index['runs'] = [copy.deepcopy(self.index['runs'][0]) for _ in range(128)]
        for i, row in enumerate(self.index['runs']):
            row['run_id'] = str(i)
            row['selection_index'] = i
        _, data, html = self.render()
        self.assertEqual(len(data['runs']), 128)
        self.assertEqual(Elements(html).tags.count('details'), 128)

    def test_real_export_join_and_sequence_validation(self):
        raw = json.dumps(dict(schema=1, run_id='0', case_id='SAME_CASE',
                              records=[dict(sequence=1, name='event', data={'flag': False})])).encode()
        (self.root / 'records.json').write_bytes(raw)
        report = json.loads((self.root / '0.json').read_text())
        report['capture'] = dict(status='saved', completion='interrupted', path='records.json', count=1,
                                 sha256=hashlib.sha256(raw).hexdigest())
        (self.root / '0.json').write_text(json.dumps(report))
        selection = dict(schema=1, name='Joined', runs=[dict(result='0.json', stand='bench')])
        bundle = self.root / 'bundle'
        self.assertEqual(pipeline(self.root, selection, bundle), 0)
        self.index = result_index.load(bundle / 'index.json')[0]
        exported = result_index.load(bundle / 'export.json')[0]
        code, summary, _ = self.render(exported=exported)
        self.assertEqual(code, 0)
        self.assertEqual(summary['runs'][0]['verdict'], 'FAIL')
        self.assertEqual(summary['runs'][0]['export']['records'], 1)
        exported['records'][0]['sequence'] = 2
        with self.assertRaisesRegex(ValueError, 'count'):
            self.render('invalid', exported=exported)

    def test_cli_and_no_overwrite(self):
        index = self.root / 'index.json'
        index.write_text(json.dumps(self.index))
        command = [sys.executable, '-m', 'stm32_gdbtest', 'results', 'report', '--root', str(self.root),
                   '--index', str(index), '--output', str(self.root / 'cli'), '--theme', 'light']
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)  # A complete diagnostic report, not a hidden UNKNOWN.
        html = self.root / 'cli/campaign.html'
        self.assertTrue(html.is_file())
        digest = hashlib.sha256(html.read_bytes()).hexdigest()
        repeated = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(hashlib.sha256(html.read_bytes()).hexdigest(), digest)
