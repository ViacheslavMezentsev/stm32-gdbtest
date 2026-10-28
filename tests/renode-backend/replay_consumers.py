"""Replay saved runs through offline consumers, without GDB or modifying sources."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from stm32_gdbtest import report_data, report_summary, result_export, result_index, result_report
from stm32_gdbtest.results import Limits
p=argparse.ArgumentParser()
p.add_argument('--runs',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
paths=sorted(a.runs.glob('*/result.json'))
if not paths:raise SystemExit('No explicit campaign runs')
rows=[]
for i,path in enumerate(paths):
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    r=report_data.read(path)
    incomplete=report_data.evidence.unavailable(r)
    bundle=result_export.export([path],a.output/str(i))
    view=report_summary.build(path)
    selection=dict(schema=1,campaign_id=str(i),name='Offline replay',runs=[dict(result='result.json',stand='emulator')])
    index=result_index.build(path.parent,selection)
    code=result_report.report(path.parent,index,a.output/('html-'+str(i)),Limits())
    assert index['runs'][0]['verdict']==r['status']
    if incomplete:
        assert bundle['command_code']==2 and not bundle['records'] and not bundle['measurements']
        assert view['analysis']=='partial' and code==2
        assert 'Incomplete evidence' in (a.output/('html-'+str(i))/'campaign.html').read_text(encoding='utf-8')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    rows.append(dict(case=r['id'],scenario=r['status'],incomplete=incomplete,ok=True))
(a.output/'replay.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('Verified',len(rows),'saved runs; no target access')
