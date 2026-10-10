"""Bounded stand campaigns over the public CLI; Target and firmware remain unchanged."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest import __version__
from stm32_gdbtest.backends import load_stand
from stm32_gdbtest.config_transport import loads as load_capsule
from stm32_gdbtest.probes import family
from stm32_gdbtest.processes import probe_identity
from stm32_gdbtest.result_capture import read as read_records


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer {low}..{high}')
    return value


def load_plan(path):
    plan = tomllib.loads(path.read_text(encoding='utf-8'))
    if set(plan) - {'schema', 'stand', 'cycles', 'interval_s', 'on_fail', 'min_free_mib', 'cases'}:
        raise ValueError('Unknown plan field')
    if type(plan.get('schema')) is not int or plan['schema'] != 1:
        raise ValueError('Plan schema must be 1')
    plan['cycles'] = integer(plan.get('cycles', 1), 1, 10000, 'cycles')
    plan['interval_s'] = integer(plan.get('interval_s', 0), 0, 86400, 'interval_s')
    plan['min_free_mib'] = integer(plan.get('min_free_mib', 256), 1, 1048576, 'min_free_mib')
    plan.setdefault('on_fail', 'stop')
    if plan['on_fail'] not in ('stop', 'continue'):
        raise ValueError('on_fail must be stop or continue')
    plan['stand'] = resolve_input(path.parent, plan.get('stand'))
    if not isinstance(plan.get('cases'), list) or not 1 <= len(plan['cases']) <= 64:
        raise ValueError('Choose 1..64 cases explicitly')
    for case in plan['cases']:
        if set(case) - {'package', 'id', 'allow_skip', 'timeout_s'}:
            raise ValueError('Unknown case field')
        if not isinstance(case.get('id'), str) or not case['id'].strip():
            raise ValueError('A case needs a nonempty id')
        case['package'] = resolve_input(path.parent, case.get('package'))
        case.setdefault('allow_skip', False)
        if type(case['allow_skip']) is not bool:
            raise ValueError('allow_skip must be bool')
        case['timeout_s'] = integer(case.get('timeout_s', 60), 1, 3600, 'timeout_s')
    return plan


def resolve_input(parent, name):
    if not isinstance(name, str) or not name:
        raise ValueError('Missing input path')
    path = (parent / Path(name).expanduser()).resolve()
    if not path.is_file():
        raise ValueError(f'Input is not a file: {path}')
    return path


def runtime_hash():
    paths = sorted((ROOT / 'stm32_gdbtest').rglob('*.py')) + [Path(__file__)]
    value = hashlib.sha256()
    for path in paths:
        value.update(path.relative_to(ROOT).as_posix().encode())
        value.update(path.read_bytes())
    return value.hexdigest()


@contextmanager
def loop_lock(stand):
    # Separate from the runner's per-attempt probe lock: no nested lock inheritance.
    key = probe_identity(stand['serial'], stand['backend'], family=family(stand))
    path = Path(tempfile.gettempdir()) / ('stm32-gdbtest-loop-' + key + '.lock')
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(pid=os.getpid(), created=stamp())))
    try:
        yield
    finally:
        path.unlink()


class Stop:
    def __init__(self, path):
        self.path = path
        self.signalled = False

    def request(self, *_):
        self.signalled = True

    def __call__(self):
        return self.signalled or self.path.exists()


def command(args, log):
    # The runner owns GDB/server lifetimes. SIGINT/SIGTERM requests stop after its cleanup.
    options = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
               if os.name == 'nt' else {'start_new_session': True})
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', '-B', str(ROOT / 'stm32_gdbtest/cli.py'),
                                    *map(str, args)], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, **options)
        return process.wait()


def validate(path, code, case, package_hash, backend):
    report = json.loads(path.read_text(encoding='utf-8'))
    status = report.get('status')
    codes = {'PASS': 0, 'FAIL': 1, 'ERROR': 2, 'SKIP': 77}
    if (report.get('id') != case['id'] or report.get('mode') != 'hardware'
            or status not in codes or code != codes[status] or report.get('command_code') != code):
        raise ValueError('Inconsistent scenario identity, mode or exit code')
    if status == 'ERROR':
        raise ValueError('Scenario infrastructure ERROR; inspect result and logs')
    if report.get('package', {}).get('sha256') != package_hash:
        raise ValueError('Run does not identify the selected package')
    if (report.get('image_verified') is not True or report.get('teardown') != 'reset_run'
            or report.get('cleanup_error') or report.get('teardown_error') or report.get('artifact_error')):
        raise ValueError('Image, cleanup or capture not confirmed')
    if backend == 'st-util' and report.get('shutdown_wait', {}).get('ready') is not True:
        raise ValueError('st-util shutdown readiness not confirmed')
    if report.get('capture', {}).get('status') != 'saved':
        raise ValueError('Required records not saved')
    records = read_records(path.parent, report)
    tree = ET.parse(path.with_name('junit.xml'))
    failures, errors, skipped = (list(tree.iter(tag)) for tag in ('failure', 'error', 'skipped'))
    cases = list(tree.iter('testcase'))
    if (len(cases) != 1 or cases[0].get('name') != case['id'] or errors
            or len(failures) != int(status == 'FAIL') or len(skipped) != int(status == 'SKIP')):
        raise ValueError('JUnit differs from result.json')
    if status == 'SKIP':
        if not report.get('skip_reason') or skipped[0].get('message') != report['skip_reason']:
            raise ValueError('SKIP reason missing or inconsistent')
        if not case['allow_skip']:
            raise ValueError('Unexpected SKIP')
    elif status == 'PASS' and any(row.get('passed') is not True for row in report.get('checks', [])):
        raise ValueError('PASS contains unsuccessful checks')
    return status, len(records['records'])


def snapshot(plan, output):
    inputs = output / 'inputs'
    inputs.mkdir()
    stand = load_stand(plan['stand'])
    if stand.get('remote'):
        raise ValueError('First stand_loop supports local stands only; run it on the stand host')
    shutil.copy2(plan['stand'], inputs / 'stand.toml')
    plan['stand'] = inputs / 'stand.toml'
    copies = {}
    for case in plan['cases']:
        source = case['package']
        if source not in copies:
            destination = inputs / f'p{len(copies):03d}.zip'
            shutil.copy2(source, destination)
            copies[source] = destination
        case['package'] = copies[source]
        with zipfile.ZipFile(case['package']) as bundle:
            info = bundle.getinfo('ddtt-package.json')
            if info.file_size > 1024 * 1024:
                raise ValueError('Package manifest too large')
            manifest = json.loads(bundle.read(info))
            if manifest.get('configuration') != 'config.json' or bundle.getinfo('config.json').file_size > 16 * 1024 * 1024:
                raise ValueError('A captured session configuration is required')
            if not load_capsule(bundle.read('config.json').decode('utf-8')).capture_results:
                raise ValueError('Enable [results] capture=true before packing')
        if (manifest.get('schema') != 1 or manifest.get('format') != 'ddtt-package'
                or manifest.get('tool_version') != __version__):
            raise ValueError('Use packages from this stm32-gdbtest version')
        if case['id'] not in [row['id'] for row in manifest['tests']]:
            raise ValueError('Selected case missing from package')
    hashes = {p.relative_to(output).as_posix(): digest(p) for p in inputs.iterdir()}
    return stand, hashes


def process_cycle(folder, selection, invoke):
    write(folder / 'selection.json', selection)
    processing = {}
    if selection['runs']:
        for name, args in (
            ('export', ['export', '--selection', folder / 'selection.json', '--output', folder / 'export']),
            ('verify', ['verify', '--index', folder / 'export/index.json', '--output', folder / 'integrity.json']),
            ('report', ['report', '--index', folder / 'export/index.json', '--export', folder / 'export/export.json',
                        '--output', folder / 'report'])):
            try:
                processing[name] = invoke(['results', *args, '--root', folder], folder / (name + '.log'))
            except Exception as error:
                processing[name] = str(error)
    return processing


# ТЗ 5.25: finite external campaign; unknown outcomes stop before the next MCU operation.
def run(plan_path, output, stop=None, invoke=command):
    plan = load_plan(plan_path)
    output.mkdir(parents=True, exist_ok=False)
    stop = stop or Stop(output / 'STOP')
    summary = dict(schema=1, state='RUNNING', started=stamp(), tool_version=__version__,
                   cycles=[], counts=dict(PASS=0, FAIL=0, ERROR=0, SKIP=0), code=2)
    write(output / 'summary.json', summary)
    try:
        shutil.copy2(plan_path, output / 'plan.toml')
        stand, hashes = snapshot(plan, output)
        baseline = runtime_hash()
        write(output / 'inputs.json', dict(files=hashes, runtime_sha256=baseline, tool_version=__version__))
        with loop_lock(stand):
            def guard():
                if runtime_hash() != baseline or any(digest(output / p) != value for p, value in hashes.items()):
                    raise ValueError('Campaign input/runtime changed')
                if shutil.disk_usage(output).free < plan['min_free_mib'] * 1024 * 1024:
                    raise ValueError('Insufficient free space; no artifacts removed')

            guard()
            if stop():
                summary.update(state='STOPPED', code=130)
                return 130
            summary['doctor_code'] = invoke(['doctor', '--stand', plan['stand']], output / 'doctor.log')
            if summary['doctor_code']:
                raise ValueError('Doctor failed; no scenarios started')
            # All cases must pass preflight before the first hardware operation.
            for index, case in enumerate(plan['cases']):
                guard()
                if stop():
                    summary.update(state='STOPPED', code=130)
                    return 130
                args = ['run', '--package', case['package'], '--test', case['id'], '--stand', plan['stand']]
                prep = output / 'prepare' / f't{index:03d}'
                code = invoke([*args, '--workdir', prep, '--prepare-only'], output / f'prepare-{index:03d}.log')
                reports = list(prep.rglob('result.json'))
                if code or len(reports) != 1:
                    raise ValueError('Preparation failed; no hardware started')
                evidence = json.loads(reports[0].read_text(encoding='utf-8'))
                if evidence.get('status') != 'PASS' or evidence.get('mode') != 'prepare':
                    raise ValueError('Preparation outcome not confirmed')
            for number in range(1, plan['cycles'] + 1):
                if stop():
                    summary.update(state='STOPPED', code=130)
                    break
                folder = output / f'c{number:05d}'
                folder.mkdir()
                cycle = dict(number=number, state='RUNNING', runs=[], processing={})
                selection = dict(schema=1, name=f'Stand cycle {number}', runs=[])
                write(folder / 'summary.json', cycle)
                try:
                    for index, case in enumerate(plan['cases']):
                        guard()
                        if stop():
                            cycle['state'] = 'STOPPED'
                            break
                        work = folder / f't{index:03d}'
                        row = dict(id=case['id'], allow_skip=case['allow_skip'], status='UNKNOWN')
                        cycle['runs'].append(row)
                        write(folder / 'summary.json', cycle)
                        row['code'] = invoke(['run', '--package', case['package'], '--test', case['id'],
                            '--stand', plan['stand'], '--workdir', work, '--timeout', case['timeout_s']],
                            folder / f't{index:03d}.log')
                        reports = list(work.rglob('result.json'))
                        if len(reports) != 1:
                            raise ValueError('Missing unique result; no retry')
                        path = reports[0]
                        report = json.loads(path.read_text(encoding='utf-8'))
                        row.update(status=report.get('status', 'UNKNOWN'), result=path.relative_to(folder).as_posix())
                        artifacts = {'junit': path.with_name('junit.xml').relative_to(folder).as_posix()}
                        selection['runs'].append(dict(result=row['result'], stand=family(stand), artifacts=artifacts))
                        if row['status'] in summary['counts']:
                            summary['counts'][row['status']] += 1
                        status, row['records'] = validate(path, row['code'], case, digest(case['package']), stand['backend'])
                        guard()
                        print(f'cycle {number} {case["id"]}: {status}', flush=True)
                        if status == 'FAIL' and plan['on_fail'] == 'stop':
                            cycle['state'] = 'FAILED'
                            break
                    if cycle['state'] == 'RUNNING':
                        cycle['state'] = 'FAILED' if any(r['status'] == 'FAIL' for r in cycle['runs']) else 'COMPLETED'
                    if cycle['state'] == 'COMPLETED' and all(r['status'] == 'SKIP' for r in cycle['runs']):
                        raise ValueError('Nothing tested: cycle contains only SKIP')
                except Exception as error:
                    cycle.update(state='ERROR', error=str(error))
                cycle['processing'] = process_cycle(folder, selection, invoke)
                if any(value != 0 for value in cycle['processing'].values()):
                    cycle.update(state='ERROR', processing_error='Evidence processing failed')
                cycle['finished'] = stamp()
                write(folder / 'summary.json', cycle)
                # Publish last: a reviewer must ignore RUNNING directories without review.json.
                write(folder / 'review.json', dict(schema=1, read_only=True, root='.', state=cycle['state'],
                    summary='summary.json', selection='selection.json', report='report/campaign.json'
                    if (folder / 'report/campaign.json').exists() else None,
                    instruction='Read stm32-gdbtest-results; inspect packaged scenario sources under t*/; '
                                'report observations and limits; do not rerun or alter tests.'))
                summary['cycles'].append(dict(number=number, state=cycle['state'], path=folder.name))
                write(output / 'summary.json', summary)
                if cycle['state'] == 'ERROR':
                    summary.update(state='ERROR', code=2)
                    break
                if cycle['state'] == 'STOPPED' or stop():
                    summary.update(state='STOPPED', code=130)
                    break
                if cycle['state'] == 'FAILED' and plan['on_fail'] == 'stop':
                    summary.update(state='FAILED', code=1)
                    break
                if number < plan['cycles']:
                    end = time.monotonic() + plan['interval_s']
                    while time.monotonic() < end and not stop():
                        time.sleep(min(0.2, max(0, end - time.monotonic())))
            if summary['state'] == 'RUNNING':
                summary.update(state='FAILED' if summary['counts']['FAIL'] else 'COMPLETED',
                               code=1 if summary['counts']['FAIL'] else 0)
    except Exception as error:
        summary.update(state='ERROR', error=str(error), code=2)
    finally:
        summary['finished'] = stamp()
        write(output / 'summary.json', summary)
    return summary['code']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new campaign directory, never overwritten')
    args = parser.parse_args()
    output = args.output.resolve()
    stop = Stop(output / 'STOP')
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, stop.request)
    try:
        return run(args.plan.resolve(), output, stop)
    except Exception as error:
        print(f'Stand loop: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
