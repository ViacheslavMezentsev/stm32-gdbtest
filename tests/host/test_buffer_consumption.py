"""Host-модель не заменяет GDB call; анализ требует доставку, потребление и восстановление."""
import copy
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'tests/buffer-consumption'
spec = importlib.util.spec_from_file_location('buffer_consumption_analysis', EXAMPLE/'analysis.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class BufferConsumptionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'host g++ required')
    def test_same_cpp_model_on_host(self):
        p = subprocess.run([sys.executable, str(EXAMPLE/'run.py'), '--host-only'], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_inventory_and_style(self):
        from stm32_gdbtest.collect import collect
        self.assertEqual({c['id'] for c in collect([EXAMPLE])}, set(analysis.EXPECTED))
        p = subprocess.run([sys.executable, str(ROOT/'tests/host/test_scenario_style.py'),
                            str(EXAMPLE/'test_buffer.py')], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def fixture(self, name='HW_BUFFER_PACKETS'):
        status, method, packets, returned, counters = analysis.EXPECTED[name]
        report = dict(id=name, status=status, mode='emulator', image_verified=True, cleanup='VERIFIED',
                      execution_cleanup='VERIFIED', capture={'status': 'saved'},
                      evidence={'diagnostics_total': 0, 'stores': {'records': {'state': 'complete'}}}, checks=[])
        records = [dict(name='restoration', data=dict(verified=True, bytes=analysis.SECTION_BYTES,
                            before_sha256='a'*64, after_sha256='a'*64))]
        if status == 'ERROR':
            report['primary_error'] = dict(type='RuntimeError',
                message='buffer-consumption: intentional exception before call')
            records.append(dict(name='interruption', data={'stage': 'before-call', 'bytes': 7}))
        else:
            data = dict(method=method, packets=packets, returned=returned, scope='software-buffer',
                        excluded=list(analysis.EXCLUDED))
            data.update(zip(analysis.COUNTERS, counters))
            records.append(dict(name='observation', data=data))
        if status == 'FAIL': report['checks'] = [dict(name='пакет опыта потреблён', passed=False)]
        if name == 'HW_BUFFER_BOUNDS': report['checks'] = [dict(name='Pointer за границей массива', passed=True)]
        return report, records

    def test_expected_fail_and_error_preserve_source(self):
        for name, expected in analysis.EXPECTED.items():
            report, records = self.fixture(name)
            saved = copy.deepcopy((report, records))
            verdict = analysis.assess(name, {'PASS': 0, 'FAIL': 1, 'ERROR': 2}[expected[0]], report, records)
            self.assertEqual(verdict['analysis'], 'PASS')
            self.assertEqual(verdict['scenario'], expected[0])
            self.assertEqual((report, records), saved)

    def test_buffer_write_without_consumption_is_not_pass(self):
        report, records = self.fixture()
        records[1]['data']['sequence'] = 0
        with self.assertRaisesRegex(ValueError, 'consumption oracle'):
            analysis.assess('HW_BUFFER_PACKETS', 0, report, records)

    def test_wrong_order_or_return_is_not_delivery(self):
        for mode in ('order', 'returned', 'method'):
            report, records = self.fixture()
            data = records[1]['data']
            if mode == 'order': data['packets'] = list(reversed(data['packets']))
            elif mode == 'returned': data['returned'] = [1, 0]
            else: data['method'] = 'buffer-write-only'
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'delivery evidence'):
                analysis.assess('HW_BUFFER_PACKETS', 0, report, records)

    def test_reentry_must_leave_current_packet_busy(self):
        report, records = self.fixture('HW_BUFFER_REENTRY')
        records[1]['data']['busy'] = 0
        with self.assertRaisesRegex(ValueError, 'consumption oracle'):
            analysis.assess('HW_BUFFER_REENTRY', 0, report, records)

    def test_bounds_without_early_refusal_is_refused(self):
        report, records = self.fixture('HW_BUFFER_BOUNDS')
        report['checks'] = []
        with self.assertRaisesRegex(ValueError, 'early refusal'):
            analysis.assess('HW_BUFFER_BOUNDS', 0, report, records)

    def test_missing_duplicate_or_failed_restoration(self):
        for mode in ('missing', 'duplicate', 'hash', 'verified', 'size'):
            report, records = self.fixture()
            if mode == 'missing': records.pop(0)
            elif mode == 'duplicate': records.append(copy.deepcopy(records[0]))
            elif mode == 'hash': records[0]['data']['after_sha256'] = 'b'*64
            elif mode == 'verified': records[0]['data']['verified'] = False
            else: records[0]['data']['bytes'] = 32
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                analysis.assess('HW_BUFFER_PACKETS', 0, report, records)

    def test_incomplete_or_dma_claims_refused(self):
        for mode in ('truncated', 'cleanup', 'hardware', 'capture', 'scope', 'excluded'):
            report, records = self.fixture()
            if mode == 'truncated': report['evidence']['stores']['records']['state'] = 'truncated'
            elif mode == 'cleanup': report['execution_cleanup'] = 'ERROR'
            elif mode == 'hardware': report['mode'] = 'hardware'
            elif mode == 'capture': report['capture']['status'] = 'unavailable'
            elif mode == 'scope': records[1]['data']['scope'] = 'dma-buffer'
            else: records[1]['data']['excluded'] = ['physical-signal']
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                analysis.assess('HW_BUFFER_PACKETS', 0, report, records)

    def test_wrong_failure_or_exception_is_not_expected_control(self):
        report, records = self.fixture('HW_BUFFER_UNCONSUMED')
        report['checks'][0]['name'] = 'unrelated failure'
        with self.assertRaisesRegex(ValueError, 'failed check'):
            analysis.assess('HW_BUFFER_UNCONSUMED', 1, report, records)
        report, records = self.fixture('HW_BUFFER_EXCEPTION')
        report['primary_error']['message'] = 'other error'
        with self.assertRaisesRegex(ValueError, 'unexpected exception'):
            analysis.assess('HW_BUFFER_EXCEPTION', 2, report, records)
