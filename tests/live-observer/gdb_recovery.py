"""GDB recovery entrypoint, always supervised by a bounded external process."""
import gdb, json, sys, subprocess, re, traceback, hashlib
from pathlib import Path
C = json.loads(Path(OBSERVER_CONFIG).read_text(encoding='utf-8'))
sys.path.insert(0, C['source'])
from recovery import backup, restore, validate, check

def ex(command):
    print('OBSERVER RECOVERY ' + command, flush=True)
    return gdb.execute(command, to_string=True)

class IO:

    def __init__(self):
        self.connected = False

    def connect(self):
        if not self.connected:
            ex('set confirm off')
            ex('set pagination off')
            ex('set remotetimeout 5')
            ex('set trust-readonly-sections off')
            ex('set stack-cache off')
            ex('set code-cache off')
            ex('target extended-remote 127.0.0.1:' + str(C['port']))
            self.connected = True

    def read(self, a, n):
        return bytes(gdb.selected_inferior().read_memory(a, n))

    def write(self, a, data):
        gdb.selected_inferior().write_memory(a, data)

    def halted(self):
        return gdb.selected_thread() is not None and gdb.selected_thread().is_stopped()

    def halt(self):
        ex('monitor halt')

    def reset_halt(self):
        ex('monitor reset halt')

    def capture_before_reset(self, d, g):
        state = self.state()
        for name, a, n in [('flash', 0x8000000, g['flash_size']), ('ram', 0x20000000, g['ram_size'])]:
            data = self.read(a, n)
            check(data == self.read(a, n), 'unstable pre-reset ' + name)
            (Path(d) / ('pre-reset-' + name + '.bin')).write_bytes(data)
        state['system'] = {hex(a): self.read(a, n).hex() for a, n in [(0xe0002000, 40), (0xe000ed08, 4), (0xe000e100, 32), (0xe000e200, 32), (0xe000e300, 32), (0xe000e400, 128)]}
        (Path(d) / 'pre-reset-state.json').write_text(json.dumps(state, indent=2))

    def qualify(self, g, i):
        check(g.get('serial') == C['geometry'].get('serial'), 'backup serial mismatch')
        self.connect()
        self.halt()
        check(self.halted(), 'halt failed')
        ident = int.from_bytes(self.read(i['address'], 4), 'little')
        check(ident & i['mask'] == i['value'], 'identity mismatch')
        size = int.from_bytes(self.read(g['flash_size_address'], 2), 'little') * 1024
        check(size == g['flash_size'], 'Flash size mismatch')
        mmap = ex('maintenance packet qXfer:memory-map:read::0,fff').replace('\\x0a', '\n').replace('\\x0d', '\n')
        check(any((int(a, 16) == 0x8000000 and int(b, 16) == g['sector'] for a, b in re.findall('<memory type="flash" start="(0x[0-9a-fA-F]+)" length="[^"]+">\\s*<property name="blocksize">(0x[0-9a-fA-F]+)</property>', mmap))), 'unconfirmed erase geometry')
        if C['action'] == 'recover':
            from recovery_fpb import clear_owned
            clear_owned(self, C)
        fp = int.from_bytes(self.read(0xe0002000, 4), 'little')
        revision = fp >> 28
        count = fp >> 4 & 15 | fp >> 8 & 112
        check(revision in (0, 1) and count <= 16, 'unknown FPB')
        for n in range(count):
            check(not int.from_bytes(self.read(0xe0002008 + 4 * n, 4), 'little') & 1, 'active FPB comparator')
        dwt = 0 if g['cpu'] == 'cortex-m0' else int.from_bytes(self.read(0xe0001000, 4), 'little') >> 28
        for n in range(dwt):
            check(not int.from_bytes(self.read(0xe0001028 + 16 * n, 4), 'little') & 15, 'active DWT comparator')

    def state(self):
        ex('maintenance flush register-cache')
        return {name: int(gdb.parse_and_eval('$' + name)) for name in ('pc', 'sp', 'xPSR', 'primask')}

    def program(self, path):
        ex('load ' + json.dumps(Path(path).as_posix()))

    def make_restore(self, flash, sector, elf):
        raw = Path(flash).read_bytes()[:sector]
        p = Path(elf).with_suffix('.bin')
        p.write_bytes(raw)
        subprocess.run([C['objcopy'], '-I', 'binary', '-O', 'elf32-littlearm', '-B', 'arm', '--rename-section', '.data=.text,alloc,load,readonly,code,contents', '--change-section-address', '.data=0x08000000', str(p), str(elf)], check=True, timeout=20)
        out = Path(elf).with_suffix('.roundtrip.bin')
        subprocess.run([C['objcopy'], '-O', 'binary', str(elf), str(out)], check=True, timeout=20)
        check(out.read_bytes() == raw, 'restore ELF roundtrip')
io = IO()
status = 2
try:
    if C['action'] == 'backup':
        backup(io, C['backup'], C['geometry'], C['identity'])
    elif C['action'] == 'load':
        m, data = validate(C['backup'])
        g = C['geometry']
        elf = Path(C['image'])
        binary = elf.with_suffix('.bin').read_bytes()
        check(hashlib.sha256(elf.read_bytes()).hexdigest() == g['elf_sha256'], 'ELF hash mismatch')
        check(hashlib.sha256(binary).hexdigest() == g['bin_sha256'] and len(binary) <= g['sector'], 'BIN hash/bounds')
        io.qualify(g, C['identity'])
        io.halt()
        check(io.read(0x8000000, g['flash_size']) == data['flash'], 'Flash changed since backup')
        io.program(elf)
        check(io.read(0x8000000, len(binary)) == binary, 'neutral image readback')
        check(io.read(0x8000000 + g['sector'], g['flash_size'] - g['sector']) == data['flash'][g['sector']:], 'Flash outside first block changed')
        io.reset_halt()
        check(io.halted(), 'halt after neutral load')
    else:
        restore(io, C['backup'])
    status = 0
except BaseException:
    traceback.print_exc()
finally:
    if io.connected:
        try:
            check(io.halted(), 'not halted at disconnect')
            ex('disconnect')
        except BaseException:
            status = 2
            traceback.print_exc()
    gdb.execute('quit ' + str(status))
