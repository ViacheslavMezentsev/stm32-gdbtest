"""SKIP control flow, evidence and refusal regression without GDB."""
import tempfile
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

from stm32_gdbtest.errors import ApiError, CheckFailed
from stm32_gdbtest.scenario import ScenarioSkipped, invoke, skip
from stm32_gdbtest.records import Journal
from stm32_gdbtest.result_capture import save, finalize
from stm32_gdbtest.reports import write_reports
from stm32_gdbtest.result_index import build


class SkipTests(unittest.TestCase):
    def test_run_hw_group_policy(self):
        path = Path(__file__).resolve().parents[1] / 'firmware/run_hw.py'
        spec = importlib.util.spec_from_file_location('skip_run_hw', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = dict(status='SKIP', command_code=77, skip_reason='reason', image_verified=True, teardown='reset_run')
        self.assertTrue(module.permitted_skip(77, report, 'HW_SKIP', ['HW_SKIP']))
        self.assertFalse(module.permitted_skip(77, report, 'HW_SKIP', []))
        for change in (dict(command_code=2), dict(status='ERROR'), dict(skip_reason=' '),
                       dict(teardown='failed'), dict(image_verified=False)):
            self.assertFalse(module.permitted_skip(77, dict(report, **change), 'HW_SKIP', ['HW_SKIP']))
        for statuses, accepted, nothing in [([], False, False), (['SKIP'], True, True),
                (['PASS', 'SKIP'], True, False), (['FAIL', 'SKIP'], False, False),
                (['ERROR', 'SKIP'], False, False), (['UNKNOWN'], False, False)]:
            result = module.step_summary([dict(status=s) for s in statuses])
            self.assertEqual(result['accepted'], accepted)
            self.assertEqual(result['nothing_tested'], nothing)
            self.assertEqual(result['passed'], statuses.count('PASS'))

    def target(self, limit=32):
        journal = Journal()
        target = SimpleNamespace(report={'checks': []}, _config={'api': {'records': {'max_text_bytes': limit}}},
                                 records=journal.records, record=journal.record)
        target.skip = lambda reason: skip(target, reason)
        return target

    def test_stops_preserves_records_and_finally(self):
        target = self.target()
        events = []
        def case(t):
            try:
                t.record('capability', False)
                t.skip('not available')
                events.append('unreachable')
            except Exception:
                events.append('swallowed')
            finally:
                events.append('finally')
        with self.assertRaises(ScenarioSkipped):
            invoke(case, target)
        self.assertEqual(events, ['finally'])
        self.assertEqual(target.records()[0]['data'], False)

    def test_reason_validation(self):
        for reason in ('', '  ', 1, None, '\ud800', 'é' * 17):
            with self.subTest(reason=repr(reason)), self.assertRaises(ApiError):
                self.target().skip(reason)
        with self.assertRaises(ScenarioSkipped):
            self.target().skip('é' * 16)

    def test_active_error_and_failure_cannot_be_skipped(self):
        for error in (OSError('I/O'), CheckFailed('failed')):
            target = self.target()
            try:
                raise error
            except Exception:
                with self.assertRaises(type(error)) as caught:
                    target.skip('hide')
                self.assertIs(caught.exception, error)

    def test_recorded_failed_check_survives_catch(self):
        target = self.target()
        target.report['checks'] = [dict(name='failed', passed=False, actual=0, expected=1)]
        with self.assertRaises(CheckFailed):
            target.skip('hide')
        with self.assertRaises(CheckFailed):
            invoke(lambda t: None, target)

    def test_intercepted_skip_is_error(self):
        def caught(t):
            try:
                t.skip('reason')
            except BaseException:
                pass
        with self.assertRaisesRegex(ApiError, 'caught skip'):
            invoke(caught, self.target())

    def test_finally_error_overrides_skip(self):
        def case(t):
            try:
                t.skip('reason')
            finally:
                raise OSError('cleanup')
        with self.assertRaises(OSError) as caught:
            invoke(case, self.target())
        self.assertIsInstance(caught.exception.__context__, ScenarioSkipped)

    def test_capture_junit_and_index_accept_77(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            t = self.target()
            t.record('capability', False)
            report = dict(id='HW_SKIP', run_id='run', status='SKIP', skip_reason='not applicable',
                          duration_s=0, mode='hardware')
            save(path, report, t, 'interrupted')
            finalize(path, report, True)
            self.assertEqual(report['command_code'], 77)
            write_reports(path, report)
            self.assertEqual(ET.parse(path/'junit.xml').find('testcase/skipped').get('message'), 'not applicable')
            index = build(path, dict(schema=1, name='skip', runs=[dict(result='result.json', stand='test')]))
            self.assertEqual(index['runs'][0]['command_code'], 77)
            self.assertNotIn('invalid command_code', index['runs'][0]['diagnostics'])
            (path/'records.json').write_text('{}')
            finalize(path, report, True)
            write_reports(path, report)
            self.assertEqual(report['status'], 'SKIP')
            self.assertEqual(report['command_code'], 2)
            self.assertEqual(len(ET.parse(path/'junit.xml').findall('testcase/error')), 1)
