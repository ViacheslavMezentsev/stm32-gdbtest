"""Build and exercise the real runner; results stay under build/renode-backend."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.runner import run
from stm32_gdbtest.collect import collect

p = argparse.ArgumentParser()
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--renode', required=True)
a = p.parse_args()
b = Path(__file__).resolve().parent
out = ROOT / 'build/cpp-call' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out.mkdir(parents=True)
suffix = '.exe' if sys.platform == 'win32' else ''
bin = a.toolchain / 'bin'
elf = out / 'firmware.elf'
cmd = [str(bin / ('arm-none-eabi-g++' + suffix)), '-mcpu=cortex-m3', '-mthumb', '-O0', '-g3', '-nostdlib', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none', '-T', str(b/'startup.ld'), str(ROOT/'tests/renode-startup/cpp_contracts.cpp'), '-o', str(elf)]
subprocess.run(cmd, check=True)
stand = out / 'stand.toml'
stand.write_text((b/'stand.example.toml').read_text().replace('executable = "renode"', 'executable = '+json.dumps(Path(a.renode).as_posix())).replace('"platform.repl"', json.dumps((b/'platform.repl').as_posix())), encoding='utf-8')
session = dict(root=str(ROOT), elf=str(elf), profile=str(b/'target.toml'), session_config=str(b/'session.toml'), gdb=str(bin/('arm-none-eabi-gdb-py3'+suffix)), out=str(out/'runs'), stand=str(stand), tests=str(b))
(out/'session.json').write_text(json.dumps(session), encoding='utf-8')
cases = {t['id']:t for t in collect([b])}
results = []
for name in ('HW_CPP_SYNC', 'HW_CPP_ASYNC'):
    code = run(session, cases[name])
    path = sorted((out/'runs').glob('*/result.json'))[-1]
    result = json.loads(path.read_text())
    ok = code == 0 and result['status'] == 'PASS' and result.get('cleanup') == 'VERIFIED'
    results.append(dict(case=name, ok=ok, result=str(path)))
(out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
raise SystemExit(0 if all(r['ok'] for r in results) else 1)
