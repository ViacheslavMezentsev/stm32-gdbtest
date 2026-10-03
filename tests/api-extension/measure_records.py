"""Offline journal cost study; executable in CPython or GDB Python, no MCU."""
import gc
import hashlib
import json
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

from evidence import Journal, RecordError


def graph_bytes(value):
    """Reachable Python object sizes, deduplicated; not RSS or allocator capacity."""
    seen = set()

    def visit(item):
        if id(item) in seen:
            return 0
        seen.add(id(item))
        size = sys.getsizeof(item)
        if isinstance(item, dict):
            size += sum(visit(k) + visit(v) for k, v in item.items())
        elif isinstance(item, (list, tuple)):
            size += sum(visit(v) for v in item)
        return size
    return visit(value)


def timed(fn, repeats=9, batch=10):
    fn()  # warm up separately
    values = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        for _ in range(batch):
            fn()
        values.append((time.perf_counter_ns() - start) / batch / 1000)
    return {'median_us': statistics.median(values), 'max_batch_mean_us': max(values),
            'batch_mean_us': values, 'batch': batch}


def memory(fn):
    gc.collect()
    tracemalloc.start()
    result = fn()
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, {'retained_bytes': retained, 'peak_bytes': peak}


def run(output):
    nested = 1
    for _ in range(8):
        nested = [nested]
    cases = [
        ('samples_10', 10, {'vdda_mv': 3300, 'temperature_c': 25.5}, {}),
        ('samples_128', 128, {'vdda_mv': 3300, 'temperature_c': 25.5}, {}),
        ('nodes_4096', 1, list(range(4094)), {}),
        ('text_65536', 1, 'x' * 65535, {}),
        ('unicode_near_65536', 1, '\U0001f600' * 16383, {}),
        ('dict_nodes_4096', 1, {str(i): i for i in range(2047)}, {}),
        ('depth_8', 1, nested, {}),
        ('integer_256', 128, (1 << 256) - 1, {}),
        ('samples_1024', 1024, {'vdda_mv': 3300, 'temperature_c': 25.5},
         {'max_records': 1024, 'max_nodes': 32768, 'max_text_bytes': 524288}),
        ('nodes_32768', 1, list(range(32766)), {'max_nodes': 32768}),
        ('text_524288', 1, 'x' * 524287, {'max_text_bytes': 524288}),
        ('integer_1024', 128, (1 << 1024) - 1, {'max_integer_bits': 1024}),
        ('depth_32', 1, None, {'max_depth': 32}),
    ]
    deep = 1
    for _ in range(32):
        deep = [deep]
    cases[-1] = ('depth_32', 1, deep, {'max_depth': 32})
    report = {'schema': 1, 'hardware': False, 'python': platform.python_version(),
              'platform': sys.platform, 'pointer_bits': 64 if sys.maxsize > 2**32 else 32,
              'journal_sha256': hashlib.sha256(Path(__file__).with_name('evidence.py').read_bytes()).hexdigest(),
              'cases': [], 'boundary_checks': [],
              'method': {'repeats': 9, 'batch': 10, 'warmup': 1,
                         'gc_enabled': gc.isenabled(),
                         'memory': 'separate tracemalloc run; input preallocated; graph sizes deduplicate identities',
                         'timing': 'perf_counter_ns; batch means include build and result disposal; not worst-case latency'}}
    try:
        import gdb
        report['gdb'] = gdb.VERSION
    except ImportError:
        report['gdb'] = None
    for name, count, data, limits in cases:
        def build():
            journal = Journal(**limits)
            for _ in range(count):
                journal.record('s', data)
            return journal
        journal = build()
        assert len(journal.records()) == count
        row = {'name': name, 'records': count, 'overrides': limits,
               'write_batch': timed(build), 'read_all': timed(journal.records),
               'read_missing': timed(lambda: journal.records('missing'))}
        measured, row['write_memory'] = memory(build)
        copies, row['read_memory'] = memory(measured.records)
        many, row['ten_reads_memory'] = memory(lambda: [measured.records() for _ in range(10)])
        row['journal_graph_bytes'] = graph_bytes(measured.__dict__)
        row['journal_and_copy_graph_bytes'] = graph_bytes([measured.__dict__, copies])
        assert len(many) == 10
        report['cases'].append(row)
    # Exact accepted boundary and rejected next value, with independent budgets.
    for name, good, bad, limits in [
        ('nodes', [0] * 4094, [0] * 4095, {}),
        ('text_bytes', 'x' * 65535, 'x' * 65536, {}),
        ('integer_bits', (1 << 256)-1, 1 << 256, {}),
        ('depth', nested, [nested], {}),
    ]:
        Journal(**limits).record('s', good)
        journal = Journal(**limits)
        def reject():
            try:
                journal.record('s', bad)
            except RecordError:
                return
            raise AssertionError('boundary accepted: ' + name)
        timing = timed(reject)
        assert journal.records() == []
        journal.record('s', 1)
        assert journal.records()[0]['sequence'] == 1
        report['boundary_checks'].append({'limit': name, 'status': 'PASS', 'rejection': timing})
    full = Journal()
    for _ in range(128):
        full.record('s', 1)
    try:
        full.record('s', 1)
    except RecordError:
        assert len(full.records()) == 128
    else:
        raise AssertionError('record count exceeded')
    report['boundary_checks'].append({'limit': 'records', 'status': 'PASS'})
    report['status'] = 'PASS'
    Path(output).write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    run(sys.argv[1])
