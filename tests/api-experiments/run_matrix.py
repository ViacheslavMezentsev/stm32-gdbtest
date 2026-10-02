"""Bounded F411 research matrix with explicit stand, GDBs and restore session.

Defaults to preparation only. --execute enables hardware, baseline and restoration.
Every attempt is retained; failure stops the matrix and still attempts restoration.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from unittest.mock import patch
from lab.openocd_native import native_swd

ROOT = Path(__file__).resolve().parent
MODULE = ROOT.parents[1]
sys.path.insert(0, str(MODULE))
from stm32_gdbtest.build_manifest import digest, load_verified
from stm32_gdbtest.collect import collect
from stm32_gdbtest.backends import load_stand
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.runner import run
from stm32_gdbtest import openocd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--restore-session', required=True, type=Path)
    parser.add_argument('--stand', required=True, type=Path)
    parser.add_argument('--gdb', required=True, action='append', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--suite', choices=('r1', 'r2', 'r3', 'r4', 'r5'), default='r1')
    parser.add_argument('--test', action='append', help='explicit subset; recorded in the protocol')
    parser.add_argument('--native-stlink', action='store_true', help='consumer-only native DAP/SWD comparison')
    parser.add_argument('--failure-paths-only', action='store_true',
                        help='exercise expected serialization ERROR and host timeout, then positive control')
    args = parser.parse_args()
    if args.failure_paths_only and args.suite != 'r1':
        parser.error('--failure-paths-only belongs to r1')
    stand = load_stand(args.stand)
    if stand['backend'] != 'openocd' or stand['flash'] != 'if-different':
        raise ValueError('This experiment requires OpenOCD and if-different flashing')
    sessions = [json.loads(p.read_text(encoding='utf-8')) for p in (args.session, args.restore_session)]
    for session in sessions:
        load_verified(session['build_manifest'], digest(session['elf']), session['profile'])
        if load_profile(session['profile'])['mcu'] != 'STM32F411CEU6':
            raise ValueError('Both firmware images must target STM32F411CEU6')
    prefix = 'HW_' + args.suite.upper() + '_'
    cases = [c for c in collect(sessions[0]['tests']) if c['id'].startswith(prefix)]
    suffixes = {
        'r1': ('VALUES', 'FRAMES', 'RAM', 'STOPS', 'RECORD', 'CONTROL'),
        'r2': ('CONDITION', 'HITCOUNT', 'RETURN', 'FINISH', 'STEP', 'WATCH', 'CALL', 'ASM'),
        'r3': ('COMMANDS', 'DEADLINE', 'SAMEVALUE', 'LANGUAGE'),
        'r4': ('NATURAL', 'OUTPUT', 'ERROR', 'SHORT'),
        'r5': tuple(kind + '_' + mode for kind in ('WIDE', 'FLOAT', 'STRUCT')
                    for mode in ('FINISH', 'RETURN', 'CALL')) + ('STRUCT_SRET',),
    }[args.suite]
    if {c['id'] for c in cases} != {prefix + s for s in suffixes}:
        raise ValueError('Unexpected research scenario inventory')
    if args.test:
        if not set(args.test) <= {c['id'] for c in cases}:
            raise ValueError('Selected test is outside the suite')
        cases = [c for c in cases if c['id'] in args.test]
    restores = {c['id']: c for c in collect(sessions[1]['tests'])}
    if not {'HW_BOOT', 'HW_GPIO'} <= restores.keys():
        raise ValueError('Restore image needs HW_BOOT and HW_GPIO controls')
    for gdb in args.gdb:
        if not gdb.is_file():
            raise ValueError('Missing GDB: ' + str(gdb))
    out = ROOT / 'build/evidence' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True)
    summary = dict(status='ERROR', hardware=args.execute, suite=args.suite, stages=[],
                   openocd_interface='native-dap-swd' if args.native_stlink else 'hla',
                   selected_tests=[c['id'] for c in cases],
                   elf_sha256=digest(sessions[0]['elf']), restore_sha256=digest(sessions[1]['elf']))
    summary['source_sha256'] = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p)
                                for p in sorted(ROOT.rglob('*')) if p.is_file()
                                and 'build' not in p.relative_to(ROOT).parts
                                and '__pycache__' not in p.relative_to(ROOT).parts}

    def execute(label, session, case, gdb, prepare, expected=0):
        runs = out / label
        # All generated outputs stay inside this consumer. Inputs may be read-only external files.
        current = dict(session, root=str(ROOT), out=str(runs), gdb=str(gdb.resolve()))
        if args.native_stlink:
            original = openocd.server_command
            with patch.object(openocd, 'server_command',
                              side_effect=lambda *a: native_swd(original(*a))):
                code = run(current, case, stand_path=args.stand, prepare_only=prepare)
        else:
            code = run(current, case, stand_path=args.stand, prepare_only=prepare)
        reports = list(runs.glob('*/result.json'))
        if len(reports) != 1:
            raise RuntimeError('Expected exactly one report for ' + label)
        report = json.loads(reports[0].read_text(encoding='utf-8'))
        summary['stages'].append(dict(label=label, status=report['status'], code=code,
                                      report=str(reports[0].relative_to(out)),
                                      gdb=report.get('gdb_version'), teardown=report.get('teardown')))
        if code != expected or report['status'] != ('PASS' if expected == 0 else 'ERROR'):
            raise RuntimeError('Failed stage: ' + label)
        if not prepare and expected == 0 and (not report.get('image_verified') or report.get('teardown') != 'reset_run'):
            raise RuntimeError('Missing verified image/reset_run: ' + label)
        return report, reports[0].parent

    try:
        # All preflights, including restore, precede the first server connection.
        for index, gdb in enumerate(args.gdb):
            for case in cases:
                execute(f'prepare_gdb{index}_{case["id"]}', sessions[0], case, gdb, True)
        for name in ('HW_BOOT', 'HW_GPIO'):
            execute('prepare_restore_' + name, sessions[1], restores[name], args.gdb[0], True)
        if args.execute:
            try:
                for name in ('HW_BOOT', 'HW_GPIO'):
                    execute('baseline_' + name, sessions[1], restores[name], args.gdb[0], False)
                for index, gdb in enumerate(args.gdb):
                    if args.failure_paths_only:
                        negative = out / 'negative-tests'
                        negative.mkdir(exist_ok=True)
                        (negative / 'test_errors.py').write_text(
                            'from stm32_gdbtest import case\nfrom lab.session import Research\n'
                            'import json, os, time\nfrom pathlib import Path\n'
                            '@case("HW_R1_SERIALIZATION_ERROR")\n'
                            'def serialization(t):\n'
                            '    with Research(t, (0x20000000, 1)) as r:\n'
                            '        r.record("before_failure", {"retained": True})\n'
                            '        r.record("invalid", object())\n'
                            '@case("HW_R1_TIMEOUT", timeout_s=5)\n'
                            'def timeout(t):\n'
                            '    t.reach("sum_bytes")\n'
                            '    request=json.loads(Path(os.environ["STM32_GDBTEST_RUN"]).read_text())\n'
                            '    Path(request["result"]).with_name("entered.txt").write_text("sum_bytes")\n'
                            '    time.sleep(30)\n', encoding='utf-8')
                        negative_session = dict(sessions[0], tests=str(negative))
                        for case in collect(negative):
                            report, directory = execute(f'negative_gdb{index}_{case["id"]}',
                                                        negative_session, case, gdb, False, expected=2)
                            if case['id'] == 'HW_R1_SERIALIZATION_ERROR':
                                if ('TypeError' not in report.get('error', '') or
                                        report.get('research') != {'before_failure': {'retained': True}}):
                                    raise RuntimeError('Serialization failure lost prior evidence')
                            elif (not (directory / 'entered.txt').exists()
                                  or 'TimeoutExpired' not in report.get('error', '')
                                  or report.get('teardown') != 'reset_run (host recovery)'):
                                raise RuntimeError('Timeout did not exercise entered scenario and recovery')
                            control = next(c for c in cases if c['id'] == 'HW_R1_CONTROL')
                            execute(f'after_gdb{index}_{case["id"]}', sessions[0], control, gdb, False)
                        continue
                    # Initial run plus three predetermined repeats, never retry-on-error.
                    for repeat in range(4):
                        for case in cases:
                            execute(f'gdb{index}_round{repeat}_{case["id"]}', sessions[0], case, gdb, False)
            except BaseException as exc:
                summary['primary_error'] = str(exc)
                raise
            finally:
                summary['restored'] = False
                try:
                    for name in ('HW_BOOT', 'HW_GPIO'):
                        execute('restore_' + name, sessions[1], restores[name], args.gdb[0], False)
                    summary['restored'] = True
                except BaseException as exc:
                    summary['restore_error'] = str(exc)
                    raise
        summary['status'] = 'PASS'
    except BaseException as exc:
        summary['error'] = str(exc)
        raise
    finally:
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        print('Evidence:', out, flush=True)


if __name__ == '__main__':
    main()
