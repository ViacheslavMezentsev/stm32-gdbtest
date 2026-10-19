"""Fault injection at every transport read, write and durable journal boundary."""
from pathlib import Path
import struct, json, datetime, hashlib, shutil
from fpb_adapter import Adapter, CTRL, REMAP, COMP, JsonLog

class Transport:

    def __init__(self, fault=None):
        self.mem = {}
        self.events = []
        self.reads = 0
        self.writes = 0
        self.fault = fault
        self.stopped = True
        self.store(CTRL, struct.pack('<10I', 609, 0x20000000, 0x48008183, 0, 0, 0, 0, 0, 0, 0))
        self.store(0x20008300, bytes(range(32)))
        self.original = dict(self.mem)

    def store(self, a, b):
        for i, x in enumerate(b):
            self.mem[a + i] = x

    def halted(self):
        return self.stopped

    def read(self, a, n):
        self.reads += 1
        self.events.append(('read', a, n))
        b = bytes((self.mem[a + i] for i in range(n)))
        if self.fault == ('read', self.reads, 'error'):
            raise OSError('read transport failure')
        if self.fault == ('read', self.reads, 'short'):
            return b[:-1]
        return b

    def write(self, a, b):
        self.writes += 1
        self.events.append(('write', a, b.hex()))
        mode = self.fault[2] if self.fault and self.fault[:2] == ('write', self.writes) else None
        if mode == 'before':
            raise OSError('write before')
        data = b
        if a == CTRL:
            data = struct.pack('<I', 608 | int.from_bytes(b, 'little') & 1)
        if a == REMAP:
            data = struct.pack('<I', 0x20000000 | int.from_bytes(b, 'little') & 0x1fffffe0)
        if mode == 'partial':
            self.store(a, data[:max(1, len(data) // 2)])
            raise OSError('partial write')
        self.store(a, data)
        if mode == 'after':
            raise OSError('lost write acknowledgement')
        if mode == 'corrupt':
            self.mem[a] ^= 1 if a == CTRL else 32
B = Path(__file__).resolve().parent
O = B.parents[1] / 'build' / ('observer-adapter-host-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
O.mkdir(parents=True)
for n in ['fpb_adapter.py', 'fpb_adapter_host.py']:
    shutil.copy2(B / n, O / n)
rows = []

def run(name, fault=None, configure=None, log_fail=None):
    t = Transport(fault)
    if configure:
        configure(t)
    events = []
    writer = JsonLog(O / (name + '.jsonl'))

    def log(e):
        events.append(e)
        if log_fail == len(events):
            raise OSError('log unavailable')
        writer(e)
    a = Adapter(t, log)
    error = None
    try:
        a.install((0x20008000, 1024), 0x20008300, 0x20008035, target=0x800021c)
    except Exception as e:
        error = str(e)
    install_reads = t.reads
    install_writes = t.writes
    installed = a.installed
    outcome = a.remove()
    before = list(t.events)
    assert a.remove() == outcome and before == t.events
    if outcome == 'VERIFIED':
        assert t.mem == t.original
    if outcome == 'NOT_NEEDED':
        assert t.writes == 0
    if error:
        assert a.primary == error
    if outcome == 'BLOCKED':
        assert a.cleanup_error
    assert len([e for e in events if e['event'] == 'intent']) >= t.writes
    r = dict(name=name, install_error=error, cleanup_error=a.cleanup_error, removal=outcome, installed=installed, install_reads=install_reads, install_writes=install_writes, reads=t.reads, writes=t.writes, events=t.events, log_events=events)
    rows.append(r)
    (O / 'results.json').write_text(json.dumps(rows, indent=2))
    return r
try:
    baseline = run('normal')
    assert baseline['installed'] and baseline['removal'] == 'VERIFIED'
    for i in range(1, baseline['writes'] + 1):
        for mode in ['before', 'after', 'partial', 'corrupt']:
            r = run('write-%02d-%s' % (i, mode), ('write', i, mode))
            if i <= baseline['install_writes']:
                assert r['install_error'] and r['removal'] == 'VERIFIED'
            else:
                assert r['removal'] == 'BLOCKED'
    for i in range(1, baseline['reads'] + 1):
        for mode in ['error', 'short']:
            r = run('read-%03d-%s' % (i, mode), ('read', i, mode))
            if i <= baseline['install_reads']:
                assert r['install_error']
            else:
                assert r['removal'] == 'BLOCKED'
    for i in range(1, len(baseline['log_events']) + 1):
        r = run('log-%02d' % i, log_fail=i)
        assert r['install_error'] or r['cleanup_error']
    run('running', configure=lambda t: setattr(t, 'stopped', False))
    for name, address, value in [('geometry', CTRL, 0x10000261), ('occupied', COMP + 20, 0x48006b91), ('literal', COMP + 24, 0x8000101), ('foreign-remap', COMP, 0x8000101)]:
        r = run(name, configure=lambda t, a=address, v=value: t.store(a, struct.pack('<I', v)))
        assert r['removal'] == 'NOT_NEEDED' and r['writes'] == 0
    summary = dict(status='PASS', checks=len(rows), hardware='NOT_RUN', baseline_reads=baseline['reads'], baseline_writes=baseline['writes'])
except Exception:
    import traceback
    (O / 'failure.txt').write_text(traceback.format_exc())
    summary = dict(status='FAIL', checks=len(rows))
    raise
finally:
    (O / 'summary.json').write_text(json.dumps(summary, indent=2))
    (O / 'SHA256SUMS.json').write_text(json.dumps({f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in O.iterdir() if f.is_file()}, indent=2))
    print(O)
    print(summary)
