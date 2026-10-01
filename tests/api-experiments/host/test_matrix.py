"""Retain the primary error when restoration also fails."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_matrix


class MatrixFailureTests(unittest.TestCase):
    def test_primary_and_restore_errors_survive_in_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / 'session.json'
            session.write_text(json.dumps(dict(build_manifest='manifest', elf='elf',
                                               profile='profile', tests='tests')))
            gdb = root / 'gdb'
            gdb.touch()
            cases = [{'id': 'HW_R1_' + suffix} for suffix in
                     ('VALUES', 'FRAMES', 'RAM', 'STOPS', 'RECORD', 'CONTROL')]
            restores = [{'id': 'HW_BOOT'}, {'id': 'HW_GPIO'}]

            def fake_run(current, case, **kwargs):
                if not kwargs['prepare_only']:
                    if Path(current['out']).name.startswith('baseline'):
                        raise RuntimeError('primary failure')
                    raise RuntimeError('restore failure')
                report = Path(current['out']) / 'run/result.json'
                report.parent.mkdir(parents=True)
                report.write_text(json.dumps(dict(status='PASS')))
                return 0

            arguments = ['run_matrix', '--session', str(session), '--restore-session', str(session),
                         '--stand', 'unused', '--gdb', str(gdb), '--execute']
            with (patch.object(run_matrix, 'ROOT', root),
                  patch.object(run_matrix, 'load_stand', return_value=dict(backend='openocd', flash='if-different')),
                  patch.object(run_matrix, 'load_profile', return_value=dict(mcu='STM32F411CEU6')),
                  patch.object(run_matrix, 'load_verified'),
                  patch.object(run_matrix, 'digest', return_value='hash'),
                  patch.object(run_matrix, 'collect', side_effect=[cases, restores]),
                  patch.object(run_matrix, 'run', side_effect=fake_run),
                  patch.object(sys, 'argv', arguments)):
                with self.assertRaisesRegex(RuntimeError, 'restore failure'):
                    run_matrix.main()
            report = json.loads(next(root.glob('build/evidence/*/summary.json')).read_text())
            self.assertEqual(report['primary_error'], 'primary failure')
            self.assertEqual(report['restore_error'], 'restore failure')
            self.assertFalse(report['restored'])
            self.assertEqual(report['status'], 'ERROR')
