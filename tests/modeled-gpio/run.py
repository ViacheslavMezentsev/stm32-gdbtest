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
a = p.parse_args()
bin = Path(a.toolchain) / 'bin' if a.toolchain else Path.home() / ('xpack-arm-none-eabi-gcc-' + a.gcc) / 'bin'
suffix = '.exe' if os.name == 'nt' else ''
out = ROOT / 'build/modeled-gpio' / ('public-candidate-renode-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
out.mkdir(parents=True)
model = out / 'gpio_model.py'
stimulus = out / 'stimulus.json'
stimulus.write_text(json.dumps(dict(generation=1, pins=2)), encoding='utf-8')
source = (B / 'model.py').read_text(encoding='utf-8') + '\n' + (B / 'peripheral.py').read_text(encoding='utf-8')
model.write_text(source.replace('@LOG@', (out / 'accesses.jsonl').as_posix()).replace('@STIMULUS@', stimulus.as_posix()), encoding='utf-8')
platform = out / 'platform.repl'
platform.write_text((ROOT / 'tests/renode-startup/platform.repl').read_text(encoding='utf-8') + f'\nmmio: Python.PythonPeripheral @ sysbus 0x40000000\n    size: 0x200\n    initable: true\n    filename: "{model.as_posix()}"\n', encoding='utf-8')
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
os.environ['GPIO_ROOT'] = str(ROOT)
os.environ['GPIO_STIMULUS'] = str(stimulus)
os.environ['GPIO_LOG'] = str(out / 'accesses.jsonl')
mapping = dict(schema=1, environment='emulator', elf_sha256=digest(elf), points=[dict(source=(B / 'fixture.cpp').relative_to(ROOT).as_posix(), source_sha256=digest(B / 'fixture.cpp'), anchor='extern "C" void ready()', scenario='GPIO_MODEL', check='RO refused before transport')])
code = renode_probe.run(ROOT, elf, platform, B / 'scenario.py', mapping, out / 'runs', str(bin / ('arm-none-eabi-gdb-py3' + suffix)), a.renode, 'GPIO_MODEL', 60)
versions = {}
for key, exe in [('gcc', bin / ('arm-none-eabi-g++' + suffix)), ('gdb', bin / ('arm-none-eabi-gdb-py3' + suffix))]:
    versions[key] = subprocess.check_output([str(exe), '--version'], text=True, timeout=15)
(out / 'versions.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
raise SystemExit(code)
