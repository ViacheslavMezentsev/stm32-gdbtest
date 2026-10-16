"""Public Target.mmio regression with an independent peripheral access log."""
import json
import os
import sys
from pathlib import Path
from dataclasses import replace
import gdb
ROOT = Path(os.environ['MMIO_ROOT'])
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.configuration import load_session
from stm32_gdbtest.svd import parse
from stm32_gdbtest.target import Target
from stm32_gdbtest.mmio import MMIO, GdbTransport

checks, observations = [], []
log = Path(os.environ['MMIO_LOG'])
config = load_session(ROOT / 'tests/mmio-renode/session.toml')
t = Target({'checks': []}, dict(config.config['target']), config)

def events():
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

def check(name, passed):
    checks.append(dict(name=name, passed=bool(passed)))

def run(name, action):
    # Отдельный управляющий регистр модели сбрасывает состояние без записи в журнал.
    gdb.selected_inferior().write_memory(0x40000100, b'\x01\0\0\0')
    start = len(events())
    try:
        result, error = action(), None
    except Exception as exc:
        result, error = None, dict(code=getattr(exc, 'code', None),
                                  effect=getattr(exc, 'effect', None), message=str(exc))
    row = dict(case=name, result=result, error=error, accesses=events()[start:])
    observations.append(row)
    return row

status = 'ERROR'
try:
    gdb.Breakpoint('ready', temporary=True, internal=True)
    gdb.execute('continue')
    row = run('WO', lambda: t.mmio.write('MODEL.WO', 42))
    check('SVD WO write one callback', row['error'] is None and
          [(e['direction'], e['offset'], e['width']) for e in row['accesses']] == [('W', 4, 4)] and
          row['result']['verified'] is False)
    for name, expected in [('RTC', [15, 0]), ('FIFO', [11, 22]), ('TICKS', [1, 2])]:
        row = run(name, lambda n=name: [t.mmio.read('MODEL.' + n, allow_effects=True) for _ in range(2)])
        check(name + ' exactly two reads', row['result'] == expected and len(row['accesses']) == 2)
    row = run('W1C', lambda: t.mmio.write('MODEL.W1C', 1, allow_effects=True))
    check('W1C one write', row['error'] is None and len(row['accesses']) == 1 and row['accesses'][0]['after'] == 14)
    for name, action in [('WO read', lambda: t.mmio.read('MODEL.WO')),
                         ('RTC write', lambda: t.mmio.write('MODEL.RTC', 1)),
                         ('RTC consent', lambda: t.mmio.read('MODEL.RTC')),
                         ('W1C consent', lambda: t.mmio.write('MODEL.W1C', 1))]:
        row = run(name, action)
        check(name + ' no access', row['error'] and row['error']['effect'] == 'none' and not row['accesses'])
    for width in (8, 16, 32):
        reg = replace(config.svd_catalog.registers['MODEL.WO'], width=width)
        row = run('width ' + str(width), lambda r=reg: t.mmio.write('MODEL.WO', 42, override=r, reason='Model supports all widths'))
        check('width ' + str(width), row['error'] is None and len(row['accesses']) == 1 and row['accesses'][0]['width'] == width // 8)
    # Ошибка после фактического эффекта не должна провоцировать повторную запись.
    original = t.mmio._transport.write
    def lose_ack(*args):
        original(*args)
        raise TimeoutError('injected ACK loss')
    t.mmio._transport.write = lose_ack
    row = run('lost ACK', lambda: t.mmio.write('MODEL.WO', 42))
    t.mmio._transport.write = original
    check('lost ACK unknown no retry', row['error'] and row['error']['effect'] == 'unknown' and len(row['accesses']) == 1)
    # Намеренно неверный SVD: описание не доказывает отсутствие аппаратного эффекта.
    raw = (ROOT / 'tests/mmio-renode/teaching-expanded.svd').read_bytes()
    bad = MMIO(parse(raw.replace(b'<readAction>clear</readAction>', b'')), GdbTransport(gdb, dict(config.config['target'])), t.record)
    row = run('missing effect', lambda: [bad.read('MODEL.RTC') for _ in range(2)])
    check('negative control detects incorrect SVD', row['result'] == [15, 0])
    for name, offset in [('MODEL.SLOTS.DATA1', 4), ('MIRROR.PORT.DATA1', 4)]:
        row = run(name, lambda n=name: t.mmio.write(n, 42))
        check(name, row['error'] is None and len(row['accesses']) == 1 and row['accesses'][0]['offset'] == offset)
    status = 'PASS' if all(c['passed'] for c in checks) else 'FAIL'
finally:
    out = Path(os.environ['DDTT_PROBE_RESULT'])
    out.with_name('observations.json').write_text(json.dumps(observations, indent=2))
    out.write_text(json.dumps(dict(status=status, checks=checks), indent=2))
    out.with_name('records.json').write_text(json.dumps(t.records(), indent=2))
    observed = next((r['result'] for r in observations if r['case'] == 'missing effect'), None)
    out.with_name('negative-control.json').write_text(json.dumps(dict(status='FAIL' if observed != [15, 15] else 'PASS', expected=[15, 15], observed=observed)))
    t.close()
