"""Build and run the supported neutral observer cases using the Renode backend."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

from prepare import B, ROOT, build, sha
from sealed import validate

sys.path.insert(0, str(ROOT))
from stm32_gdbtest.collect import collect
from stm32_gdbtest.runner import run

UNSUPPORTED = {'HW_OBSERVER_FPB_ZERO', 'HW_OBSERVER_FPB_SEVEN', 'HW_OBSERVER_COMBINED', 'HW_OBSERVER_FPB_EXCEPTION'}


def assess(case_id, result, records, code, environment='emulator'):
    """Expected failures must have the intended cause and verified cleanup.

    The emulator route reports its own process cleanup in `cleanup`; a hardware result has no such field and
    instead needs a verified execution cleanup, the verified image and the reset_run teardown.
    """
    expected = ('ERROR' if case_id in ('HW_OBSERVER_EXCEPTION', 'HW_OBSERVER_ACTIVE', 'HW_OBSERVER_FPB_EXCEPTION') else
                'FAIL' if case_id == 'HW_OBSERVER_NEGATIVE' else 'PASS')
    clean = any(row.get('name') == 'observer_cleanup' and
                row.get('data', {}).get('status') == 'VERIFIED' for row in records)
    marker = 'intentional active ISR' if case_id == 'HW_OBSERVER_ACTIVE' else 'intentional before resume'
    reason = expected != 'ERROR' or marker in (result.get('error') or '')
    if expected == 'FAIL':
        checks = result.get('checks', [])
        reason = any(row.get('name') == 'ISR count' and row.get('passed') is False for row in checks)
    return {'case': case_id, 'expected': expected, 'status': result.get('status'),
            'ok': result.get('status') == expected and code == {'PASS': 0, 'FAIL': 1, 'ERROR': 2}[expected]
            and clean and reason and teardown_ok(result, environment)
            and not result.get('cleanup_error') and not result.get('teardown_error')}


def teardown_ok(result, environment):
    if environment == 'hardware':
        return (result.get('execution_cleanup') == 'VERIFIED' and result.get('image_verified') is True
                and result.get('teardown') == 'reset_run')
    return result.get('cleanup') == 'VERIFIED'


def save(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain', required=True)
    parser.add_argument('--gdb', required=True, help='GDB with Python support')
    parser.add_argument('--renode', required=True)
    parser.add_argument('--out', type=Path, help='New output directory; defaults to build/live-observer/<UTC>')
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = (args.out or ROOT / 'build/live-observer' / stamp).resolve()
    manifest = build(args.toolchain, out)
    validate(out)
    (out / 'platform.repl').write_bytes((ROOT / 'tests/renode-startup/platform.repl').read_bytes())
    (out / 'target.toml').write_text('''schema = 3
environment = "emulator"
architecture = "cortex-m"
name = "NeutralObserver"
mcu = "CortexM"
flash_start = 0x08000000
flash_size = 65536
breakpoint_limit = 4
fault_handlers = []
core_registers = ["pc", "sp"]
[diagnostic_registers]
''', encoding='utf-8')
    (out / 'session.toml').write_text('[config]\ntarget = "target.toml"\n[results]\ncapture = true\n', encoding='utf-8')
    (out / 'stand.toml').write_text('schema = 1\n[emulator]\nbackend = "renode"\nexecutable = ' +
                                  json.dumps(Path(args.renode).as_posix()) + '''
startup_timeout_s = 15
shutdown_timeout_s = 5
[renode]
platform = "platform.repl"
''', encoding='utf-8')
    # This explicit compiler build is not a Ninja dependency snapshot.
    build_manifest = dict(schema=1, evidence='neutral single-source compiler invocation',
                          elf_sha256=sha(out / 'neutral.elf'), profile_sha256=sha(out / 'target.toml'),
                          compilers=[dict(name='arm-none-eabi-gcc', version=manifest['compiler'])],
                          units=[dict(source='tests/live-observer/neutral.c',
                                      flags=['-mcpu=cortex-m4', '-mthumb', '-mfloat-abi=soft', '-O0', '-g3'])],
                          inputs=[dict(file='tests/live-observer/' + name, sha256=digest)
                                  for name, digest in manifest['sources'].items()],
                          library_versions=[], cube_packages=[],
                          limitations=['Toolchain headers and binary installation are not hashed'])
    save(out / 'build-manifest.json', build_manifest)
    mapping = json.loads((B / 'map.template.json').read_text(encoding='utf-8'))
    mapping['elf_sha256'] = sha(out / 'neutral.elf')
    from tools.ddtt_guard import validate_point
    from tools.ddtt_coverage import export
    for point in mapping['points']:
        validate_point(ROOT, point)
        point['source_sha256'] = sha(ROOT / point['source'])
    save(out / 'map.json', mapping)
    os.environ['LIVE_OBSERVER_BUNDLE'] = str(out)
    session = dict(root=str(ROOT), elf=str(out / 'neutral.elf'), profile=str(out / 'target.toml'),
                   session_config=str(out / 'session.toml'), gdb=args.gdb, out=str(out / 'runs'),
                   stand=str(out / 'stand.toml'), tests=str(B), build_manifest=str(out / 'build-manifest.json'))
    cases = collect([B])
    if len(cases) != 12 or not UNSUPPORTED <= {case['id'] for case in cases}:
        raise RuntimeError('scenario inventory changed')
    rows = []
    save(out / 'unsupported.json', [{'case': name, 'status': 'NOT_SUPPORTED',
                                    'reason': 'This Renode platform does not implement FPB remap'}
                                   for name in sorted(UNSUPPORTED)])
    for case in cases:
        if case['id'] in UNSUPPORTED:
            continue
        before = set((out / 'runs').glob('*/result.json'))
        code = run(session, case)
        paths = set((out / 'runs').glob('*/result.json')) - before
        if len(paths) != 1:
            raise RuntimeError('missing or ambiguous result')
        path = paths.pop()
        result = json.loads(path.read_text(encoding='utf-8'))
        capture = path.parent / 'records.json'
        records = json.loads(capture.read_text(encoding='utf-8'))['records'] if capture.exists() else []
        row = assess(case['id'], result, records, code)
        row['result'] = path.relative_to(out).as_posix()
        rows.append(row)
        save(out / 'summary.json', rows)
    validate(out)
    save(out / 'inputs.json', {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in out.iterdir() if p.is_file() and p.name != 'inputs.json'})
    coverage = export(ROOT, mapping, list((out / 'runs').glob('*/result.json')), out / 'view')
    print(out, flush=True)
    return 0 if len(rows) == 8 and all(row['ok'] for row in rows) and len(coverage) == 3 and all(row['state'] == 'CONFIRMED' for row in coverage) else 1


if __name__ == '__main__':
    raise SystemExit(main())
