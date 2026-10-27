import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools import renode_probe
p = argparse.ArgumentParser()
p.add_argument('--gcc', default='14.2.1-1.1')
p.add_argument('--toolchain')
p.add_argument('--renode', default='C:/Program Files/Renode/renode.exe')
p.add_argument('--benchmark', action='store_true')
p.add_argument('--compact', action='store_true')
a = p.parse_args()
bin = Path(a.toolchain) / 'bin' if a.toolchain else Path.home() / ('xpack-arm-none-eabi-gcc-' + a.gcc) / 'bin'
suffix = '.exe' if os.name == 'nt' else ''
out = ROOT / 'build/mmio-renode' / ('public-candidate-renode-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
out.mkdir(parents=True)
model = out / 'mmio_model.py'
model.write_text((B / 'mmio_model.py').read_text().replace('@LOG@', (out / 'accesses.jsonl').as_posix()), encoding='utf-8')
platform = out / 'platform.repl'
platform.write_text((ROOT / 'tests/renode-startup/platform.repl').read_text() + f'\nmmio: Python.PythonPeripheral @ sysbus 0x40000000\n    size: 0x200\n    initable: true\n    filename: "{model.as_posix()}"\n', encoding='utf-8')
elf = out / 'fixture.elf'
command = [str(bin / ('arm-none-eabi-g++' + suffix)), '-mcpu=cortex-m3', '-mthumb', '-O0', '-g3', '-fno-eliminate-unused-debug-types', '-ffreestanding', '-nostdlib', '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none', '-T', str(ROOT / 'tests/renode-startup/startup.ld'), str(B / 'fixture.cpp'), '-o', str(elf)]
with (out / 'build.log').open('wb') as stream:
    subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=60)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = [*B.glob('*.py'), *B.glob('*.svd'), *B.glob('*.toml'), B / 'fixture.cpp', *(ROOT / 'stm32_gdbtest').glob('*.py'), ROOT / 'tests/renode-backend/target.toml', ROOT / 'tests/renode-startup/startup.ld', platform, model, elf]
snapshot = out / 'sources'
snapshot.mkdir()
for source in [*B.glob('*.py'), *B.glob('*.svd'), *B.glob('*.toml'), B / 'fixture.cpp']:
    (snapshot / source.name).write_bytes(source.read_bytes())
(out / 'inputs.json').write_text(json.dumps({str(f): digest(f) for f in inputs}, indent=2), encoding='utf-8')
(out / 'build-command.json').write_text(json.dumps(command), encoding='utf-8')
if (ROOT / '.git').exists():
    (out / 'git.txt').write_text(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True) + subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True))
os.environ['MMIO_ROOT'] = str(ROOT)
os.environ['MMIO_SESSION'] = str(B / ('session-compact.toml' if a.compact else 'session.toml'))
os.environ['MMIO_LOG'] = str(out / 'accesses.jsonl')
mapping = dict(schema=1, environment='emulator', elf_sha256=digest(elf), points=[dict(source=(B / 'fixture.cpp').relative_to(ROOT).as_posix(), source_sha256=digest(B / 'fixture.cpp'), anchor='extern "C" void ready()', scenario='MMIO_AUDIT', check='SVD WO write one callback')])
code = renode_probe.run(ROOT, elf, platform, B / ('scenario_benchmark.py' if a.benchmark else 'scenario.py'), mapping, out / 'runs', str(bin / ('arm-none-eabi-gdb-py3' + suffix)), a.renode, 'MMIO_AUDIT', 300 if a.benchmark else 60)
versions = {}
for key, exe in [('gcc', bin / ('arm-none-eabi-g++' + suffix)), ('gdb', bin / ('arm-none-eabi-gdb-py3' + suffix))]:
    versions[key] = subprocess.check_output([str(exe), '--version'], text=True, timeout=15)
(out / 'versions.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
raise SystemExit(code)
