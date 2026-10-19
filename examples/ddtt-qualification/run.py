"""Host demonstration with explicit synthetic evidence, not a hardware qualification."""
import argparse
import copy
import hashlib
from html import escape
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import ddtt_coverage as coverage, ddtt_qualification as qualification


def fixture(root):
    root.mkdir(parents=True, exist_ok=True)
    source = root / 'sample.py'
    source.write_bytes(Path(__file__).with_name('sample.py').read_bytes())
    elf = hashlib.sha256(b'HOST FIXTURE: no ELF and no MCU').hexdigest()
    context = dict(instance='synthetic-board', environment='host', elf_sha256=elf, inputs_sha256='b'*64)
    mapping = dict(schema=2, environment='host', elf_sha256=elf, qualification=dict(context=context,
        conditions={'clock': dict(unit='Hz', min=24900000, max=25100000, max_age_s=60)}), points=[
        dict(source='sample.py', source_sha256=coverage.digest(source), anchor='ticks += 1', scenario='HW_DEMO', check='ticks advanced', requires=['clock']),
        dict(source='sample.py', source_sha256=coverage.digest(source), anchor='ready = True', scenario='HW_DEMO', check='ready', requires=[])])
    result = dict(mode='host', purpose='automated', id='HW_DEMO', status='PASS', started_utc='2026-10-19T00:00:10Z', duration_s=2,
        elf_sha256=elf, build_manifest=dict(inputs=[dict(file='sample.py', sha256=coverage.digest(source))]),
        checks=[dict(name='ticks advanced', passed=True), dict(name='ready', passed=True)])
    snapshot = dict(schema=1, context=copy.deepcopy(context), measurements=[dict(condition='clock', value=25000000, uncertainty=10000,
        unit='Hz', observed_utc='2026-10-19T00:00:00Z', valid_until='2026-10-19T00:01:00Z', invalidated_utc=None,
        method='measured', evidence_sha256=hashlib.sha256(b'SYNTHETIC instrument record').hexdigest())])
    return mapping, result, snapshot


def demo(out):
    if out.exists():
        raise ValueError('Use a fresh output directory; old evidence is retained')
    mapping, result, snapshot = fixture(out)
    rows = []
    for name in ('nominal', 'wrong-clock', 'missing', 'stale', 'other-board', 'conflict', 'power-lost', 'declared-only', 'raw-fail', 'optional-absent'):
        m, r, s = copy.deepcopy(mapping), copy.deepcopy(result), copy.deepcopy(snapshot)
        measure = s['measurements'][0]
        if name == 'wrong-clock': measure['value'] = 16000000
        if name == 'stale': measure['valid_until'] = '2026-10-19T00:00:05Z'
        if name == 'other-board': s['context']['instance'] = 'other'
        if name == 'conflict': s['measurements'].append(copy.deepcopy(measure))
        if name == 'power-lost':
            m['qualification']['conditions']['supply'] = dict(unit='V', min=3.0, max=3.6, max_age_s=60)
            m['points'][0]['requires'].append('supply')
            supply = copy.deepcopy(measure)
            supply.update(condition='supply', unit='V', value=3.3, uncertainty=0.01, invalidated_utc='2026-10-19T00:00:11Z')
            s['measurements'].append(supply)
        if name == 'declared-only': measure['method'] = 'declared'
        if name == 'raw-fail': r['status'] = 'FAIL'; r['checks'][0]['passed'] = False
        if name == 'optional-absent':
            m['points'][0]['required'] = False
            m['qualification']['conditions']['clock'] = dict(kind='capability', unit='present', min=1, max=1, max_age_s=60)
            measure.update(value=0, uncertainty=0, unit='present')
        run = out / name; run.mkdir()
        path = run / 'result.json'; path.write_text(json.dumps(r), encoding='utf-8')
        (run / 'snapshot.json').write_text(json.dumps(s, indent=2), encoding='utf-8')
        (run / 'map.json').write_text(json.dumps(m, indent=2), encoding='utf-8')
        if name != 'missing': qualification.bind(path, s)
        projected = coverage.export(out, m, [path], run / 'view')
        p = projected[0]
        assert projected[1]['state'] == 'CONFIRMED'
        expected = 'CONFIRMED' if name == 'nominal' else 'FAILED' if name == 'raw-fail' else 'UNKNOWN'
        assert p['state'] == expected, (name, p)
        rows.append(dict(case=name, raw=p['raw_state'], applicability=p['applicability']['status'], state=p['state'],
                         reason=p['applicability']['reason'], conditions=p['applicability']['conditions']))
    (out / 'summary.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    table = ''.join('<tr>'+''.join('<td>'+escape(str(r[k]))+'</td>' for k in ('case','raw','applicability','state'))+
                    '<td><a href="'+r['case']+'/view/ddtt-evidence.json">evidence</a></td></tr>' for r in rows)
    (out / 'index.html').write_text('<meta charset="utf-8"><style>body{background:#0d1117;color:#c9d1d9;font:18px system-ui;margin:3em}td,th{padding:.6em;border-bottom:1px solid #30363d}a{color:#58a6ff}</style><h1>DDTT qualification — HOST SYNTHETIC</h1><p>No hardware or emulator measurements. Independent assertion remains confirmed.</p><table><tr><th>Case</th><th>Raw</th><th>Applicability</th><th>Final</th><th>Details</th></tr>'+table+'</table>', encoding='utf-8')
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True)
    print(json.dumps(demo(Path(p.parse_args().out)), indent=2))
