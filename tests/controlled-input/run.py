"""A5.1: host-модель и настоящие write/ret через GDB в Renode."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.collect import collect
from stm32_gdbtest.runner import run
from stm32_gdbtest.report_data import read as read_report
from stm32_gdbtest.result_capture import read as read_capture
from analysis import EXPECTED, assess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host-only', action='store_true')
    p.add_argument('--host-cxx', default='g++')
    p.add_argument('--toolchain', type=Path)
    p.add_argument('--renode', default='renode')
    a = p.parse_args()
    if not a.host_only and not a.toolchain:
        p.error('--toolchain required')
    out = ROOT / 'build/controlled-input' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    inputs = out / 'inputs'
    inputs.mkdir(parents=True)
    for f in Path(__file__).resolve().parent.iterdir():
        if f.is_file(): shutil.copy2(f, inputs / f.name)
    summary = dict(status='ERROR', mode='host' if a.host_only else 'emulator',
                   inputs={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs.iterdir()}, runs=[])
    suffix = '.exe' if sys.platform == 'win32' else ''
    def command(name, argv):
        with (out / (name + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        summary.setdefault('commands', []).append(dict(name=name, exit_code=result.returncode))
        if result.returncode: raise RuntimeError(name + ' failed')
    try:
        exe = out / ('host' + suffix)
        command('host-build', [a.host_cxx, '-DHOST', '-std=c++11', '-O0', '-Wall', '-Wextra', '-Werror',
                               str(inputs/'model.cpp'), '-o', str(exe)])
        command('host-model', [str(exe)])
        if not a.host_only:
            toolbin = a.toolchain.resolve() / 'bin'
            elf = out / 'firmware.elf'
            compiler = str(toolbin / ('arm-none-eabi-g++' + suffix))
            gdb = str(toolbin / ('arm-none-eabi-gdb-py3' + suffix))
            renode = shutil.which(a.renode) or a.renode
            for name, exe in [('arm', compiler), ('gdb', gdb), ('renode', renode)]:
                command(name + '-version', [exe, '--version'])
            command('arm-build', [compiler, '-mcpu=cortex-m3', '-mthumb', '-O0', '-g3', '-nostdlib',
                                  '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none',
                                  '-T', str(inputs/'startup.ld'), str(inputs/'model.cpp'), '-o', str(elf)])
            summary['elf_sha256'] = hashlib.sha256(elf.read_bytes()).hexdigest()
            stand = out / 'stand.toml'
            stand.write_text((inputs/'stand.example.toml').read_text(encoding='utf-8')
                .replace('executable = "renode"', 'executable = ' + json.dumps(Path(renode).as_posix()))
                .replace('"platform.repl"', json.dumps((inputs/'platform.repl').as_posix())), encoding='utf-8')
            cases = {c['id']: c for c in collect([inputs])}
            if set(cases) != set(EXPECTED): raise ValueError('scenario inventory')
            for cycle in range(2):
                for name in EXPECTED:
                    runs = out / ('runs-' + str(cycle) + '-' + name)
                    session = dict(root=str(ROOT), elf=str(elf), profile=str(inputs/'target.toml'),
                        session_config=str(inputs/'session.toml'), gdb=gdb, out=str(runs), stand=str(stand), tests=str(inputs))
                    code = run(session, cases[name])
                    files = list(runs.glob('*/result.json'))
                    if len(files) != 1: raise ValueError('ambiguous result')
                    result = read_report(files[0])
                    records = read_capture(files[0].parent, result)['records']
                    verdict = assess(name, code, result, records)
                    summary['runs'].append(dict(cycle=cycle, case=name, result=str(files[0].relative_to(out)), **verdict))
            if len(summary['runs']) != 12: raise ValueError('incomplete campaign')
        summary['status'] = 'PASS'
    except Exception as error:
        summary['error'] = str(error)
    finally:
        (out/'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
        print(out/'summary.json')
        print(summary['status'])
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
