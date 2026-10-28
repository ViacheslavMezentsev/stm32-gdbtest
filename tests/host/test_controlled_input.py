"""Host-модель не заменяет GDB ret; анализ требует потребление и восстановление."""
import copy
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'tests/controlled-input'
spec = importlib.util.spec_from_file_location('controlled_input_analysis', EXAMPLE/'analysis.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class ControlledInputTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'host g++ required')
    def test_same_cpp_model_on_host(self):
        p = subprocess.run([sys.executable, str(EXAMPLE/'run.py'), '--host-only'], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_inventory_and_style(self):
        from stm32_gdbtest.collect import collect
        self.assertEqual({c['id'] for c in collect([EXAMPLE])}, set(analysis.EXPECTED))
        p = subprocess.run([sys.executable, str(ROOT/'tests/host/test_scenario_style.py'),
                            str(EXAMPLE/'test_input.py')], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def fixture(self, name='HW_INPUT_SRAM'):
        status, method, supplied, consumed, active, reads = analysis.EXPECTED[name]
        report = dict(id=name, status=status, mode='emulator', image_verified=True, cleanup='VERIFIED',
                      execution_cleanup='VERIFIED', capture={'status': 'saved'},
                      evidence={'diagnostics_total': 0, 'stores': {'records': {'state': 'complete'}}}, checks=[])
        records = [dict(name='restoration', data=dict(verified=True, bytes=32,
                            before_sha256='a'*64, after_sha256='a'*64))]
        if status == 'ERROR':
            report['primary_error'] = dict(type='RuntimeError',
                message='controlled-input: intentional exception before consumption')
            records.append(dict(name='interruption', data={'stage': 'before-consumption', 'applied': 1}))
        else:
            records.append(dict(name='observation', data=dict(method=method, supplied=supplied, consumed=consumed,
                active=active, reads=reads, cycles=1, scope='software-input',
                excluded=['physical-signal', 'peripheral-acquisition'])))
        if status == 'FAIL': report['checks'] = [dict(name='ранняя подмена потреблена', passed=False)]
        return report, records

    def test_expected_fail_and_error_preserve_source(self):
        for name, expected in analysis.EXPECTED.items():
            report, records = self.fixture(name)
            saved = copy.deepcopy((report, records))
            verdict = analysis.assess(name, {'PASS': 0, 'FAIL': 1, 'ERROR': 2}[expected[0]], report, records)
            self.assertEqual(verdict['analysis'], 'PASS')
            self.assertEqual(verdict['scenario'], expected[0])
            self.assertEqual((report, records), saved)

    def test_write_success_without_consumption_is_not_pass(self):
        report, records = self.fixture()
        records[1]['data']['consumed'] = 0
        with self.assertRaisesRegex(ValueError, 'consumption oracle'):
            analysis.assess('HW_INPUT_SRAM', 0, report, records)

    def test_missing_duplicate_or_failed_restoration(self):
        for mode in ('missing', 'duplicate', 'hash', 'verified', 'size'):
            report, records = self.fixture()
            if mode == 'missing': records.pop(0)
            elif mode == 'duplicate': records.append(copy.deepcopy(records[0]))
            elif mode == 'hash': records[0]['data']['after_sha256'] = 'b'*64
            elif mode == 'verified': records[0]['data']['verified'] = False
            else: records[0]['data']['bytes'] = 1
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                analysis.assess('HW_INPUT_SRAM', 0, report, records)

    def test_incomplete_or_hardware_evidence_refused(self):
        for mode in ('truncated', 'cleanup', 'hardware', 'capture', 'scope'):
            report, records = self.fixture()
            if mode == 'truncated': report['evidence']['stores']['records']['state'] = 'truncated'
            elif mode == 'cleanup': report['execution_cleanup'] = 'ERROR'
            elif mode == 'hardware': report['mode'] = 'hardware'
            elif mode == 'capture': report['capture']['status'] = 'unavailable'
            else: records[1]['data']['scope'] = 'physical-input'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                analysis.assess('HW_INPUT_SRAM', 0, report, records)

    def test_wrong_failure_or_exception_is_not_expected_control(self):
        report, records = self.fixture('HW_INPUT_TOO_EARLY')
        report['checks'][0]['name'] = 'unrelated failure'
        with self.assertRaisesRegex(ValueError, 'failed check'):
            analysis.assess('HW_INPUT_TOO_EARLY', 1, report, records)
        report, records = self.fixture('HW_INPUT_EXCEPTION')
        report['primary_error']['message'] = 'other error'
        with self.assertRaisesRegex(ValueError, 'unexpected exception'):
            analysis.assess('HW_INPUT_EXCEPTION', 2, report, records)
