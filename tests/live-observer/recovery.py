"""External snapshot/recovery policy, independent of Target and testable on a fake."""
import hashlib, json
from pathlib import Path
FLASH = 0x8000000
RAM = 0x20000000

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check(ok, message):
    if not ok:
        raise RuntimeError(message)

def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')

def read(io, address, size):
    data = io.read(address, size)
    check(len(data) == size, 'short read')
    return data

def backup(io, directory, geometry, identity):
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=False)
    io.qualify(geometry, identity)
    if hasattr(io, 'capture_before_reset'):
        io.capture_before_reset(d, geometry)
    # Admission already established reset-halt; do not reset between snapshots.
    io.halt()
    check(io.halted(), 'not halted before backup')
    files = {}
    for name, address, size in [('flash', FLASH, geometry['flash_size']), ('ram', RAM, geometry['ram_size'])]:
        a = read(io, address, size)
        b = read(io, address, size)
        check(a == b, 'unstable ' + name)
        prior = d / ('pre-reset-' + name + '.bin')
        if prior.exists():
            check(prior.read_bytes() == a, 'memory changed during backup: ' + name)
        (d / (name + '.bin')).write_bytes(a)
        (d / (name + '-verify.bin')).write_bytes(b)
        check((d / (name + '.bin')).read_bytes() == a, 'disk readback')
        files[name] = {'size': size, 'sha256': digest(a)}
    io.make_restore(d / 'flash.bin', geometry['sector'], d / 'restore.elf')
    files['restore'] = {'size': (d / 'restore.elf').stat().st_size, 'sha256': digest((d / 'restore.elf').read_bytes())}
    state = io.state()
    m = {'backup': 'VERIFIED', 'geometry': geometry, 'identity': identity, 'files': files, 'state_after_reset': state}
    save(d / 'manifest.json', m)
    return m

def validate(directory):
    d = Path(directory)
    m = json.loads((d / 'manifest.json').read_text(encoding='utf-8'))
    check(m['backup'] == 'VERIFIED', 'backup not verified')
    g = m['geometry']
    check(0 < g['sector'] <= g['flash_size'] and g['ram_size'] >= 4096, 'bad geometry')
    data = {}
    for name in ('flash', 'ram', 'restore'):
        p = d / (name + ('.elf' if name == 'restore' else '.bin'))
        v = p.read_bytes()
        f = m['files'][name]
        check(len(v) == f['size'] and digest(v) == f['sha256'], 'corrupt backup ' + name)
        data[name] = v
    check(len(data['flash']) == g['flash_size'] and len(data['ram']) == g['ram_size'], 'backup bounds')
    return (m, data)

def restore(io, directory):
    d = Path(directory)
    report = {'recovery': 'ERROR', 'flash_written': False, 'ram_written': False}
    try:
        m, data = validate(d)
        g = m['geometry']
        io.qualify(g, m['identity'])
        io.halt()
        check(io.halted(), 'halt not confirmed')
        current = read(io, FLASH, g['flash_size'])
        check(current[g['sector']:] == data['flash'][g['sector']:], 'Flash outside authorized erase block changed')
        if current != data['flash']:
            report['flash_written'] = True
            save(d / 'recovery.json', report)
            io.program(d / 'restore.elf')
        # Flash programming can use SRAM: restore and verify SRAM last.
        io.reset_halt()
        check(io.halted(), 'reset halt not confirmed')
        final = read(io, FLASH, g['flash_size'])
        (d / 'flash-restored.bin').write_bytes(final)
        check(final == data['flash'], 'Flash restore mismatch')
        report['ram_written'] = True
        save(d / 'recovery.json', report)
        io.write(RAM, data['ram'])
        finalram = read(io, RAM, g['ram_size'])
        (d / 'ram-restored.bin').write_bytes(finalram)
        check(finalram == data['ram'], 'SRAM restore mismatch')
        check(io.halted(), 'target resumed during recovery')
        final_state = io.state()
        report.update(final_state=final_state, expected_state=m['state_after_reset'])
        check(final_state == m['state_after_reset'], 'CPU reset-state mismatch')
        report.update(recovery='VERIFIED', flash_sha256=digest(final), ram_sha256=digest(finalram), final_state=final_state)
    except BaseException as e:
        report['error'] = repr(e)
        raise
    finally:
        save(d / 'recovery.json', report)
    return report
