"""Build and qualify the exact neutral ELF and displaced prologue without connecting."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
B = Path(__file__).resolve().parent
ROOT = B.parents[1]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def symbols(text):
    return {r[2]: int(r[0], 16) for line in text.splitlines() if len((r := line.split())) == 3}

def build(tc, out):
    sources = {p.name: sha(p) for p in B.iterdir()
               if p.is_file() and p.suffix in ('.py', '.c', '.S', '.ld', '.toml', '.md', '.json')}
    out.mkdir(parents=True, exist_ok=False)

    def tool(n):
        return str(Path(tc) / 'bin' / ('arm-none-eabi-' + n + ('.exe' if os.name == 'nt' else '')))

    def command(n, args):
        r = subprocess.run([tool(n), *map(str, args)], capture_output=True, timeout=45)
        (out / (n + '-' + str(len(list(out.glob('*.log')))) + '.log')).write_bytes(r.stdout + r.stderr)
        r.check_returncode()
        return r.stdout.decode('utf-8')
    compiler = command('gcc', ['--version']).splitlines()[0]
    command('gcc', ['-mcpu=cortex-m4', '-mthumb', '-mfloat-abi=soft', '-O0', '-g3', '-ffreestanding', '-nostdlib', '-Wl,--build-id=none', '-Wl,-Map=' + str(out / 'neutral.map'), '-T', B / 'neutral.ld', B / 'neutral.c', '-o', out / 'neutral.elf'])
    command('objcopy', ['-O', 'binary', out / 'neutral.elf', out / 'neutral.bin'])
    sy = symbols(command('nm', [out / 'neutral.elf']))
    code = (out / 'neutral.bin').read_bytes()
    addr = sy['original_work']
    if addr % 4 or code[addr - 0x8000000:addr - 0x8000000 + 4] != bytes.fromhex('80b483b0'):
        raise ValueError('unsupported displaced prologue')
    if len(code) > 16384 or sy['__observer_start'] != 0x20008000 or sy['__observer_end'] != 0x20009000:
        raise ValueError('image/layout bounds')
    command('as', ['-mcpu=cortex-m4', '-mthumb', B / 'hook.S', '-o', out / 'hook.o'])
    command('ld', ['-Ttext=0x20008000', '-e', 'irq_hook', out / 'hook.o', '-o', out / 'hook.elf'])
    command('objcopy', ['-O', 'binary', '--only-section=.text', out / 'hook.elf', out / 'hook.bin'])
    hs = symbols(command('nm', [out / 'hook.elf']))
    if (out / 'hook.bin').stat().st_size > 768:
        raise ValueError('code overlaps remap table')
    (out / 'symbols.json').write_text(json.dumps(hs, indent=2))
    for name in ('neutral', 'hook'):
        (out / (name + '.disassembly')).write_text(command('objdump', ['-d', out / (name + '.elf')]))
    sys.path.insert(0, str(ROOT))
    from stm32_gdbtest.collect import collect
    cases = collect([B])
    if len(cases) != 12:
        raise ValueError('scenario set changed')
    for p in B.glob('*.py'):
        compile(p.read_text(encoding='utf-8'), str(p), 'exec')
    if any(sha(B / name) != digest for name, digest in sources.items()):
        raise ValueError('Sources changed during build')
    m = dict(status='OFFLINE_PREPARED', hardware='NOT_RUN', function=addr,
             continuation=(addr + 4) | 1, displaced='80b483b0', vectors=512,
             flash_size=524288, ram_size=131072, sector=16384, observer=[0x20008000, 4096],
             remap_table=0x20008300, fpb_hook=hs['fpb_hook'], cases=[c['id'] for c in cases],
             files={p.name: sha(p) for p in out.iterdir() if p.is_file()}, sources=sources,
             compiler=compiler, toolchain=str(Path(tc).resolve()))
    (out / 'manifest.json').write_text(json.dumps(m, indent=2), encoding='utf-8')
    print(json.dumps({k: m[k] for k in ('status', 'hardware', 'function', 'displaced', 'cases')}, indent=2))
    return m
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--toolchain', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    build(a.toolchain, a.out.resolve())
