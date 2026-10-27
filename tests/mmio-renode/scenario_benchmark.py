"""A2.1 real RSP writes, independent Renode callback log, no physical board."""
import importlib.util
import json
import os
from pathlib import Path
import gdb
import sys
sys.path.insert(0, str(Path(os.environ["MMIO_ROOT"])))
from stm32_gdbtest.configuration import load_session
from stm32_gdbtest.mmio import GdbTransport

root = Path(os.environ['MMIO_ROOT'])
spec = importlib.util.spec_from_file_location('mmio_benchmark', root/'tests/mmio-renode/benchmark.py')
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
out = Path(os.environ['DDTT_PROBE_RESULT'])
checks = []
try:
    gdb.Breakpoint('ready', temporary=True, internal=True)
    gdb.execute('continue')
    config = load_session(root/'tests/mmio-renode/session.toml')
    rows = bench.campaign(out.parent/'measurements', config.svd_catalog,
                          GdbTransport(gdb, dict(config.config['target'])))
    events = [json.loads(x) for x in Path(os.environ['MMIO_LOG']).read_text().splitlines()]
    checks.append(dict(name='independent callback count', passed=len(events) == 22000))
    checks.append(dict(name='one write per operation', passed=all(
        x['direction'] == 'W' and x['offset'] == 4 and x['width'] == 4 for x in events)))
    expected = [i for n in (1000, 10000) for mode in (0, 1) for i in range(n)]
    checks.append(dict(name='independent value order', passed=[x['value'] for x in events] == expected))
    checks.append(dict(name='logical journal equivalence', passed=all(
        rows[i]['logical_sha256'] == rows[i+1]['logical_sha256'] for i in (0, 2))))
finally:
    out.write_text(json.dumps(dict(status='PASS' if len(checks) == 4 and all(x['passed'] for x in checks)
                                  else 'FAIL', checks=checks), indent=2), encoding='utf-8')
