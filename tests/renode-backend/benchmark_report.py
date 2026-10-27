"""Measure accumulation only (not GDB transport), preserving all logical events."""
import gc
import json
from pathlib import Path
import sys
import time
import tracemalloc
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from stm32_gdbtest import report_data as r
results=[]
for count in (1000,10000):
    for compact in (False,True):
        gc.collect();tracemalloc.start();start=time.perf_counter()
        rows=r.EventBuffer() if compact else []
        for i in range(count):rows.append(dict(name='sequence',passed=True,actual=i,expected=i))
        elapsed=time.perf_counter()-start;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        results.append(dict(count=count,compact=compact,seconds=elapsed,current_bytes=current,peak_bytes=peak,spool_bytes=rows.spool_bytes if compact else 0))
        if compact:rows.close()
print(json.dumps(results,indent=2))
