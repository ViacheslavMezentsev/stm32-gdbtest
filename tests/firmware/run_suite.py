"""Full scenario acceptance on an explicitly selected stand, with restoration."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.backends import load_stand
from stm32_gdbtest.build_manifest import digest, load_verified
from stm32_gdbtest.collect import collect
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.runner import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--restore-session', type=Path, required=True)
    parser.add_argument('--stand', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--timeout-recovery', action='store_true')
    args = parser.parse_args()
    session, restore = [json.loads(p.read_text(encoding='utf-8'))
                        for p in (args.session, args.restore_session)]
    for data in (session, restore):
        load_verified(data['build_manifest'], digest(data['elf']), data['profile'])
    mcu = load_profile(session['profile'])['mcu']
    if mcu != load_profile(restore['profile'])['mcu']:
        raise ValueError('restore MCU differs')
    if load_stand(args.stand)['flash'] != 'if-different':
        raise ValueError('restoration requires if-different')
    cases = collect(session['tests'])
    restores = {c['id']: c for c in collect(restore['tests'])}
    restore_ids = ('HW_CI_BOOT', 'HW_CI_GPIO') if 'HW_CI_BOOT' in restores else (
        ('HW_BOOT', 'HW_GPIO') if 'HW_GPIO' in restores else ('HW_BOOT', 'HW_BLINK'))
    out = ROOT/'build/scenario-migration'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True)
    summary = dict(status='ERROR', hardware=args.execute, mcu=mcu,
                   elf_sha256=digest(session['elf']), manifest_sha256=digest(session['build_manifest']),
                   restore_elf_sha256=digest(restore['elf']), cases=len(cases), stages=[])

    def execute(label, selected, case, prepare=False, expected=0):
        # Preserve the consumer root so scenario helper imports retain their semantics.
        current = dict(selected, out=str(Path(selected['root'])/'build/scenario-migration'/out.name/label))
        code = run(current, case, args.stand, prepare_only=prepare)
        reports = list(Path(current['out']).glob('*/result.json'))
        if len(reports) != 1:
            raise RuntimeError('expected unique result: '+label)
        report = json.loads(reports[0].read_text(encoding='utf-8'))
        summary['stages'].append(dict(label=label, code=code, expected_code=expected,
                                     status=report['status'], report=str(reports[0])))
        (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        if code != expected:
            raise RuntimeError('unexpected result: '+label)
        if not prepare and expected == 0 and (not report.get('image_verified') or report.get('teardown') != 'reset_run'):
            raise RuntimeError('missing verification/reset: '+label)
        return report, reports[0].parent

    try:
        for case in cases:
            execute('prepare_'+case['id'], session, case, prepare=True)
        for identifier in restore_ids:
            execute('prepare_restore_'+identifier, restore, restores[identifier], prepare=True)
        if args.execute:
            try:
                for case in cases:
                    execute(case['id'], session, case)
                by_id = {c['id']: c for c in cases}
                for identifier in ('HW_CI_ADC_DMA', 'HW_CI_RTC_ALARM', 'HW_ADC_DMA_RUNTIME'):
                    if identifier in by_id:
                        execute('after_faults_'+identifier, session, by_id[identifier])
                if args.timeout_recovery:
                    path = out/'test_timeout.py'
                    path.write_text('from pathlib import Path\nimport os,json,time\n'
                        'def stall(t):\n'
                        '    request=json.loads(Path(os.environ["STM32_GDBTEST_RUN"]).read_text())\n'
                        '    Path(request["result"]).with_name("entered.txt").write_text("at main")\n'
                        '    time.sleep(60)\n', encoding='utf-8')
                    timeout_case = dict(id='HW_API_TIMEOUT', function='stall', path=str(path),
                                        timeout_s=5, labels=[], contracts=[])
                    report, directory = execute('timeout', session, timeout_case, expected=2)
                    if (not (directory/'entered.txt').exists() or 'TimeoutExpired' not in report.get('error', '')
                            or report.get('teardown') != 'reset_run (host recovery)'):
                        raise RuntimeError('timeout did not enter scenario and recover')
                    execute('after_recovery', session, by_id.get('HW_CI_GPIO', cases[0]))
            finally:
                failures = []
                for identifier in restore_ids:
                    try:
                        execute('restore_'+identifier, restore, restores[identifier])
                    except BaseException as error:
                        failures.append(str(error))
                if failures:
                    raise RuntimeError('; '.join(failures))
        summary['status'] = 'PASS'
    finally:
        (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print('SUITE:', out/'summary.json', flush=True)


if __name__ == '__main__':
    main()
