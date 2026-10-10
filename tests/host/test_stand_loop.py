"""Stand loop policies and artifact integrity; no debugger access (TC-171)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from tools import stand_loop as loop
from stm32_gdbtest.configuration import load_session
from stm32_gdbtest.config_transport import dumps
from stm32_gdbtest.result_capture import save, finalize
from stm32_gdbtest.reports import write_reports


class StandLoopTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'target.toml').write_bytes((loop.ROOT / 'tests/firmware/profiles/f411ce/target.toml').read_bytes())
        (self.root / 'session.toml').write_text('[config]\ntarget="target.toml"\n[results]\ncapture=true')
        self.capsule = dumps(load_session(self.root / 'session.toml'))
        with zipfile.ZipFile(self.root / 'input.zip', 'w') as z:
            z.writestr('ddtt-package.json', json.dumps(dict(schema=1, format='ddtt-package',
                tool_version=loop.__version__, configuration='config.json', tests=[dict(id='ONE'), dict(id='TWO')])))
            z.writestr('config.json', self.capsule)
        (self.root / 'stand.toml').write_text('[probe]\nbackend="st-util"\nserial="' + 'A' * 24 + '"')
        self.plan = self.root / 'plan.toml'
        self.out = self.root / 'out'
        self.text = ('schema=1\nstand="stand.toml"\ncycles=2\nmin_free_mib=1\n'
                     '[[cases]]\npackage="input.zip"\nid="ONE"\n'
                     '[[cases]]\npackage="input.zip"\nid="TWO"\nallow_skip=true\n')
        self.plan.write_text(self.text)
        self.operations = []
        self.outcomes = ['PASS', 'SKIP', 'PASS', 'SKIP']
        self.counter = 0
        self.corrupt = None
        self.stand = dict(backend='st-util', serial='A' * 24, remote=None)
        self.patches = [patch.object(loop, 'load_stand', return_value=self.stand),
                        patch.object(loop, 'runtime_hash', return_value='fixed'),
                        patch.object(loop.tempfile, 'gettempdir', return_value=str(self.root))]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def invoke(self, args, log):
        self.operations.append(args)
        log.write_text('model only\n')
        if args[0] != 'run':
            return 0
        work = Path(args[args.index('--workdir') + 1])
        work.mkdir(parents=True)
        case = args[args.index('--test') + 1]
        if '--prepare-only' in args:
            loop.write(work / 'result.json', dict(status='PASS', mode='prepare'))
            return 0
        status = self.outcomes[self.counter]
        self.counter += 1
        report = dict(id=case, run_id=f'run-{self.counter}', mode='hardware', status=status,
            checks=[dict(name='check', passed=status != 'FAIL')], duration_s=0, image_verified=True,
            teardown='reset_run', shutdown_wait=dict(ready=True),
            package=dict(sha256=loop.digest(args[args.index('--package') + 1])))
        if status == 'SKIP':
            report['skip_reason'] = 'optional'
        target = Mock()
        target.records.return_value = [dict(sequence=1, name='sample', data={'value': 0})]
        save(work, report, target, 'normal' if status == 'PASS' else 'interrupted')
        finalize(work, report, True)
        write_reports(work, report)
        if self.corrupt:
            self.corrupt(work, report)
        return report['command_code']

    def execute(self):
        code = loop.run(self.plan, self.out, invoke=self.invoke)
        return code, json.loads((self.out / 'summary.json').read_text())

    def test_two_cycles_keep_each_attempt_and_review(self):
        code, data = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(data['counts'], dict(PASS=2, FAIL=0, ERROR=0, SKIP=2))
        self.assertEqual(len(list(self.out.glob('c*/review.json'))), 2)
        self.assertEqual(len(list(self.out.glob('c*/t*/result.json'))), 4)
        with self.assertRaises(FileExistsError):
            loop.run(self.plan, self.out, invoke=self.invoke)

    def test_doctor_refusal_prevents_prepare_and_hardware(self):
        def invoke(args, log):
            self.operations.append(args)
            return 2
        self.assertEqual(loop.run(self.plan, self.out, invoke=invoke), 2)
        self.assertEqual([a[0] for a in self.operations], ['doctor'])

    def test_prepare_refusal_prevents_hardware(self):
        def invoke(args, log):
            return 2 if '--prepare-only' in args else self.invoke(args, log)
        self.assertEqual(loop.run(self.plan, self.out, invoke=invoke), 2)
        self.assertEqual(self.counter, 0)

    def test_fail_stops_by_default(self):
        self.outcomes = ['FAIL']
        code, data = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(self.counter, 1)
        self.assertEqual(data['state'], 'FAILED')

    def test_continue_fail_preserves_failure_across_later_pass(self):
        self.plan.write_text(self.text.replace('cycles=2', 'cycles=2\non_fail="continue"'))
        self.outcomes = ['FAIL', 'PASS', 'PASS', 'SKIP']
        code, data = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(self.counter, 4)
        self.assertEqual(data['counts']['FAIL'], 1)

    def test_error_or_unexpected_skip_stops_even_with_continue(self):
        self.plan.write_text(self.text.replace('cycles=2', 'cycles=2\non_fail="continue"'))
        for status in ('ERROR', 'SKIP'):
            with self.subTest(status=status):
                self.out = self.root / status
                self.counter = 0
                self.outcomes = [status]
                code, data = self.execute()
                self.assertEqual(code, 2)
                self.assertEqual(self.counter, 1)
                self.assertEqual(data['state'], 'ERROR')

    def test_all_skip_does_not_become_success(self):
        self.plan.write_text(self.text.replace('id="ONE"', 'id="ONE"\nallow_skip=true'))
        self.outcomes = ['SKIP', 'SKIP']
        code, data = self.execute()
        self.assertEqual(code, 2)
        self.assertEqual(self.counter, 2)

    def test_corrupt_records_stop_before_next_case(self):
        self.corrupt = lambda work, report: (work / 'records.json').write_text('{}')
        code, data = self.execute()
        self.assertEqual(code, 2)
        self.assertEqual(self.counter, 1)

    def test_junit_cleanup_and_capture_failures_stop(self):
        def corrupt(work, report):
            (work / 'junit.xml').write_text('<testsuite/>')
        self.corrupt = corrupt
        self.assertEqual(self.execute()[0], 2)
        self.assertEqual(self.counter, 1)

    def test_processing_failure_stops_after_current_cycle(self):
        def invoke(args, log):
            return 2 if args[:2] == ['results', 'export'] else self.invoke(args, log)
        self.assertEqual(loop.run(self.plan, self.out, invoke=invoke), 2)
        self.assertEqual(self.counter, 2)
        self.assertTrue((self.out / 'c00001/review.json').exists())

    def test_stop_file_between_cases_preserves_partial_cycle(self):
        self.corrupt = lambda work, report: (self.out / 'STOP').touch()
        code, data = self.execute()
        self.assertEqual(code, 130)
        self.assertEqual(self.counter, 1)
        self.assertEqual(data['cycles'][0]['state'], 'STOPPED')

    def test_input_change_stops_before_next_case(self):
        self.corrupt = lambda work, report: (self.out / 'inputs/p000.zip').write_bytes(b'changed')
        self.assertEqual(self.execute()[0], 2)
        self.assertEqual(self.counter, 1)

    def test_occupied_loop_lock_does_not_run_or_remove_owner(self):
        with loop.loop_lock(self.stand):
            code, data = self.execute()
            self.assertEqual(code, 2)
            self.assertEqual(self.operations, [])
            self.assertEqual(len(list(self.root.glob('*.lock'))), 1)

    def test_bad_plan_rejected_before_output_creation(self):
        for changed in ('cycles=0', 'cycles=true', 'cycles=10001'):
            with self.subTest(changed=changed):
                self.plan.write_text(self.text.replace('cycles=2', changed))
                with self.assertRaises(ValueError):
                    loop.run(self.plan, self.out, invoke=self.invoke)
                self.assertFalse(self.out.exists())

    def test_low_disk_prevents_any_command(self):
        with patch.object(loop.shutil, 'disk_usage', return_value=Mock(free=0)):
            self.assertEqual(self.execute()[0], 2)
        self.assertEqual(self.operations, [])


    def test_cleanup_capture_and_package_identity_reject_success(self):
        changes = ({'shutdown_wait': {'ready': False}}, {'cleanup_error': 'late failure'},
                   {'artifact_error': {'message': 'failed'}}, {'package': {'sha256': '0' * 64}},
                   {'mode': 'prepare'}, {'command_code': 2}, {'capture': {'status': 'unavailable'}})
        for index, change in enumerate(changes):
            with self.subTest(change=change):
                self.out = self.root / f'changed-{index}'
                self.counter = 0
                def corrupt(work, report):
                    loop.write(work / 'result.json', dict(report, **change))
                self.corrupt = corrupt
                self.assertEqual(self.execute()[0], 2)
                self.assertEqual(self.counter, 1)

    def test_missing_result_stops_without_retry(self):
        self.corrupt = lambda work, report: (work / 'result.json').unlink()
        self.assertEqual(self.execute()[0], 2)
        self.assertEqual(self.counter, 1)

    def test_stop_before_doctor_is_non_hardware(self):
        stop = loop.Stop(self.root / 'STOP')
        stop.request()
        self.assertEqual(loop.run(self.plan, self.out, stop, invoke=self.invoke), 130)
        self.assertEqual(self.operations, [])

    def test_no_capture_package_rejected_before_doctor(self):
        with zipfile.ZipFile(self.root / 'input.zip', 'w') as bundle:
            bundle.writestr('ddtt-package.json', json.dumps(dict(schema=1, format='ddtt-package',
                tool_version=loop.__version__, tests=[dict(id='ONE')])))
        self.assertEqual(self.execute()[0], 2)
        self.assertEqual(self.operations, [])

    def test_remote_stand_rejected_before_doctor(self):
        self.stand['remote'] = {'host': 'example'}
        self.assertEqual(self.execute()[0], 2)
        self.assertEqual(self.operations, [])


if __name__ == '__main__':
    unittest.main()
