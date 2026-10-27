"""Reproducible A2.1 host/GDB measurement; tracemalloc measures Python, not whole-process RSS."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.records import Journal
from stm32_gdbtest.compact_records import CompactJournal
from stm32_gdbtest.configuration import MAXIMUMS_V2
from stm32_gdbtest.mmio import MMIO, Register
from stm32_gdbtest.result_capture import save, read, finalize


def measure(folder, catalog, transport, count, mode):
    folder.mkdir(parents=True)
    cls = CompactJournal if mode == 'compact' else Journal
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    journal = cls(**MAXIMUMS_V2)
    mmio = MMIO(catalog, transport, journal.mmio_record)
    for i in range(count):
        mmio.write('MODEL.WO', i, reason='bounded benchmark')
    collect_s = time.perf_counter() - started
    retained, peak = tracemalloc.get_traced_memory()
    report = dict(run_id=folder.name, id='MMIO_SCALE', status='PASS')
    started = time.perf_counter()
    save(folder, report, SimpleNamespace(_journal=journal), 'normal')
    finalize(folder, report, True)
    capture_s = time.perf_counter() - started
    if report['command_code']:
        raise AssertionError(report)
    started = time.perf_counter()
    snapshot = read(folder, report, materialize=False)
    digest, seen = hashlib.sha256(), 0
    for row in snapshot['records']:
        digest.update(json.dumps(row, sort_keys=True, separators=(',', ':')).encode())
        seen += 1
    read_s = time.perf_counter() - started
    if seen != 2 * count:
        raise AssertionError('lost events')
    _, whole_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = dict(mode=mode, operations=count, logical_records=seen,
                  nodes=journal._nodes, text_bytes=journal._text_bytes,
                  definitions=len(journal.definitions) if mode == 'compact' else 0,
                  collect_s=collect_s, capture_s=capture_s, read_s=read_s,
                  retained_python_bytes=retained, collect_peak_python_bytes=peak,
                  whole_peak_python_bytes=whole_peak,
                  file_bytes=(folder/'records.json').stat().st_size,
                  logical_sha256=digest.hexdigest())
    (folder/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (folder/'measurement.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def campaign(out, catalog, transport, repeats=1):
    results = []
    for repeat in range(repeats):
        for count in (1000, 10000):
            pair = []
            for mode in ('full', 'compact'):
                row = measure(out/f'{repeat}-{count}-{mode}', catalog, transport, count, mode)
                row['repeat'] = repeat
                results.append(row); pair.append(row)
                (out/'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
            if pair[0]['logical_sha256'] != pair[1]['logical_sha256']:
                raise AssertionError('lossless comparison failed')
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--repeats', type=int, default=1)
    args = p.parse_args()
    catalog = SimpleNamespace(registers={'MODEL.WO': Register('MODEL.WO', 0x40000004, 32, 'write-only')}, sha256='a'*64)
    transport = SimpleNamespace(prepare=lambda: None, write=lambda *args: None)
    print(json.dumps(campaign(args.out, catalog, transport, args.repeats), indent=2))
