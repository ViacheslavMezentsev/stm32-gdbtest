"""Real runner + independent receiver journal; no board and no result rewriting."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.collect import collect
from stm32_gdbtest.runner import run
from tools import ddtt_coverage as coverage, ddtt_qualification as qualification


def save(path, data):
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')


def receipt(path):
    """Reject incomplete/ambiguous bus journals rather than reporting zero."""
    events = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    if len(events) != 3:
        raise ValueError('Expected exactly three bus events')
    for index, event in enumerate(events, 1):
        if (set(event) != {'sequence', 'offset', 'width', 'value', 'accepted'} or
                event['sequence'] != index or event['value'] != index or
                event['offset'] != 0 or event['width'] != 4 or type(event['accepted']) is not bool):
            raise ValueError('Invalid receiver journal')
    return sum(event['accepted'] for event in events)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cxx', 'gdb', 'renode'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = ROOT / 'tests/renode-backend'
    elf = out / 'firmware.elf'
    flags = ['-mcpu=cortex-m3', '-mthumb', '-O0', '-g3', '-nostdlib', '-ffreestanding',
             '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none']
    command = [a.cxx, *flags, '-T', str(base/'startup.ld'), str(B/'firmware.cpp'), '-o', str(elf)]
    save(out/'build-command.json', command)
    with (out/'build.log').open('wb') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    versions = {name: subprocess.check_output([exe, '--version'], text=True, timeout=20)
                for name, exe in [('cxx', a.cxx), ('gdb', a.gdb)]}
    save(out/'versions.json', versions)
    inputs = [B/'firmware.cpp', B/'test_receiver.py', B/'receiver.py', B/'run_renode.py',
              base/'startup.ld', base/'target.toml', base/'platform.repl', elf]
    manifest = dict(schema=1, evidence='neutral single-source compiler invocation',
                    elf_sha256=coverage.digest(elf), profile_sha256=coverage.digest(base/'target.toml'),
                    compilers=[dict(name=Path(a.cxx).name, version=versions['cxx'])],
                    library_versions=[], cube_packages=[],
                    inputs=[dict(file=f.relative_to(ROOT).as_posix(), sha256=coverage.digest(f))
                            for f in inputs if f.is_relative_to(ROOT)],
                    units=[dict(source='examples/ddtt-qualification/firmware.cpp', flags=flags)],
                    limitations=['Toolchain headers and binary installation are not hashed'])
    save(out/'build-manifest.json', manifest)
    cases = collect([B])
    case = next(c for c in cases if c['id'] == 'HW_QUALIFICATION')
    summaries = []
    for name, drop in [('nominal', 0), ('dropped-word', 2), ('nominal-repeat', 0)]:
        folder = out/name
        folder.mkdir()
        trace = folder/'receiver.jsonl'
        model = folder/'receiver.py'
        model.write_text('DROP_SEQUENCE = ' + str(drop) + '\nTRACE_PATH = ' + repr(trace.as_posix()) + '\n' +
                         (B/'receiver.py').read_text(encoding='utf-8'), encoding='utf-8')
        platform = folder/'platform.repl'
        platform.write_text((base/'platform.repl').read_text() +
                            '\nreceiver: Python.PythonPeripheral @ sysbus 0x40000000\n'
                            "    size: 0x100\n    initable: true\n    script: " +
                            json.dumps('exec(' + repr(model.read_text(encoding='utf-8')) + ')', ensure_ascii=False) +
                            '\n', encoding='utf-8')
        stand = folder/'stand.toml'
        stand.write_text('schema = 1\n[emulator]\nbackend = "renode"\nexecutable = ' +
                         json.dumps(Path(a.renode).as_posix()) + '\nstartup_timeout_s = 15\n'
                         'shutdown_timeout_s = 5\n[renode]\nplatform = "platform.repl"\n', encoding='utf-8')
        fingerprint = {str(f): coverage.digest(f) for f in [*inputs, model, platform, stand]}
        save(folder/'inputs.json', fingerprint)
        context = dict(instance=name, environment='emulator', elf_sha256=coverage.digest(elf),
                       inputs_sha256=qualification.digest(qualification.canonical(fingerprint)))
        mapping = dict(schema=2, environment='emulator', elf_sha256=coverage.digest(elf),
                       qualification=dict(context=context, conditions={
                           'receiver': dict(unit='words', min=3, max=3, max_age_s=120)}), points=[])
        for anchor, check, requires in [('sent++;', 'three sends', ['receiver']),
                                         ('initialized = 1;', 'initialized', [])]:
            mapping['points'].append(dict(source='examples/ddtt-qualification/firmware.cpp',
                source_sha256=coverage.digest(B/'firmware.cpp'), anchor=anchor,
                scenario=case['id'], check=check, requires=requires))
        save(folder/'map.json', mapping)
        session = dict(root=str(ROOT), elf=str(elf), profile=str(base/'target.toml'),
                       session_config=str(base/'session.toml'), gdb=a.gdb, out=str(folder/'preflight'),
                       stand=str(stand), tests=str(B), build_manifest=str(out/'build-manifest.json'))

        def execute():
            code = run(session, case)
            path = next(Path(session['out']).glob('*/result.json'))
            result = coverage.load(path)
            if code != 0 or result['status'] != 'PASS' or result.get('cleanup') != 'VERIFIED':
                raise RuntimeError('Probe failed: ' + str(path))
            return path

        execute()
        measured = receipt(trace)
        preflight_trace = folder/'preflight-receiver.jsonl'
        trace.rename(preflight_trace)
        now = datetime.now(timezone.utc)
        snapshot = dict(schema=1, context=context, measurements=[dict(condition='receiver',
            value=measured, uncertainty=0, unit='words', observed_utc=now.isoformat(),
            valid_until=(now+timedelta(seconds=120)).isoformat(), invalidated_utc=None,
            method='measured', evidence_sha256=coverage.digest(preflight_trace))])
        # Снимок сохранён до основной попытки. Обе машины используют неизменную модель.
        save(folder/'snapshot.json', snapshot)
        session['out'] = str(folder/'runs')
        result_path = execute()
        raw_hash = coverage.digest(result_path)
        if receipt(trace) != measured or trace.read_bytes() != preflight_trace.read_bytes():
            raise RuntimeError('Receiver changed between qualification and run')
        if any(coverage.digest(f) != checksum for f, checksum in fingerprint.items()):
            raise RuntimeError('Inputs changed')
        qualification.bind(result_path, coverage.load(folder/'snapshot.json'))
        rows = coverage.export(ROOT, mapping, [result_path], folder/'view')
        expected = 'UNKNOWN' if drop else 'CONFIRMED'
        if ([r['raw_state'] for r in rows] != ['CONFIRMED', 'CONFIRMED'] or
                [r['state'] for r in rows] != [expected, 'CONFIRMED'] or
                coverage.digest(result_path) != raw_hash):
            raise RuntimeError('Qualification projection differs from expectation')
        summaries.append(dict(case=name, received=measured, raw='PASS',
            states=[r['state'] for r in rows], applicability=rows[0]['applicability']['status'],
            result_sha256=raw_hash, result_unchanged=True, cleanup='VERIFIED'))
        save(out/'summary.json', summaries)
    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
