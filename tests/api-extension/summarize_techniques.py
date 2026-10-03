"""Verify HW pairs and export only nonlocal evidence from three run directories."""
import argparse
import hashlib
import json
from pathlib import Path


def summarize(directory):
    root = Path(directory)
    summary = json.loads((root/'summary.json').read_text(encoding='utf-8'))
    if summary['status'] != 'PASS' or not summary['hardware']:
        raise ValueError('requires completed hardware run')
    reports = {}
    stages = []
    for stage in summary['stages']:
        report = json.loads((root/stage['report']).read_text(encoding='utf-8'))
        if stage['code'] or report['status'] != 'PASS':
            raise ValueError('failed stage')
        if not stage['label'].startswith('prepare_'):
            if not report.get('image_verified') or report.get('teardown') != 'reset_run':
                raise ValueError('missing image verification or reset_run')
        reports[stage['label']] = report
        stages.append(dict(label=stage['label'], status=report['status'],
                           checks=report.get('checks', []), image_verified=report.get('image_verified'),
                           teardown=report.get('teardown'), warnings=report.get('warnings', [])))
    native_label = next(k for k in reports if k.startswith('baseline_') and k != 'baseline_HW_CI_ADC_UNITS')
    table_label = next(k for k in reports if k.startswith('experiment_HW_TECH010_'))
    if reports[native_label]['checks'] != reports[table_label]['checks']:
        raise ValueError('table pair checks differ')
    old = reports['experiment_HW_E1_MEASUREMENTS']
    new = reports['experiment_HW_TECH011_SERIES']
    extra = {'configuration matches MCU', 'configured measurement quality',
             'GDB/Python VDDA mean', 'GDB/Python temperature mean'}
    if old['checks'] != [c for c in new['checks'] if c['name'] not in extra]:
        raise ValueError('series pair checks differ')
    for report, key in ((old, 'e1_evidence'), (new, 'tech011_evidence')):
        evidence = report[key]
        if evidence['summary']['count'] != 10 or len(evidence['records']) != 11:
            raise ValueError('incomplete series or missing summary')
    return dict(mcu=new['profile']['mcu'], backend=new['backend'],
                gdb=new['gdb_version'], python=new['python_version'],
                elf_sha256=summary['elf_sha256'], manifest_sha256=summary['manifest_sha256'],
                restore_elf_sha256=summary['restore_elf_sha256'],
                table_checks_identical=True, series_original_checks_preserved=True,
                original=old['e1_evidence'], configured=new['tech011_evidence'], stages=stages)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directories', nargs=3)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    report = dict(schema=1, status='PASS', hardware=True,
                  source_sha256={name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in ('table_checks.py', 'table_variants.py', 'measurement_technique.py',
                                 'board/test_techniques.py', 'run_hw.py')},
                  boards=[summarize(directory) for directory in args.directories])
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
