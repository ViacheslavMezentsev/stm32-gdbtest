"""Build and exercise the real runner; results stay under build/renode-backend."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.runner import run
from stm32_gdbtest.collect import collect

p = argparse.ArgumentParser()
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--renode', required=True)
p.add_argument('--storage-only', action='store_true')
p.add_argument('--summary', action='store_true', help='Also compare summary output in full and compact storage')
a = p.parse_args()
b = Path(__file__).resolve().parent
out = ROOT / 'build/report-renode' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out.mkdir(parents=True)
suffix = '.exe' if sys.platform == 'win32' else ''
bin = a.toolchain / 'bin'
elf = out / 'firmware.elf'
cmd = [str(bin / ('arm-none-eabi-g++' + suffix)), '-mcpu=cortex-m3', '-mthumb', '-O0', '-g3', '-nostdlib', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none', '-T', str(b/'startup.ld'), str(b/'startup.cpp'), '-o', str(elf)]
subprocess.run(cmd, check=True)
stand = out / 'stand.toml'
stand.write_text((b/'stand.example.toml').read_text().replace('executable = "renode"', 'executable = '+json.dumps(Path(a.renode).as_posix())).replace('"platform.repl"', json.dumps((b/'platform.repl').as_posix())), encoding='utf-8')
session = dict(root=str(ROOT), elf=str(elf), profile=str(b/'target.toml'), session_config=str(b/'session.toml'), gdb=str(bin/('arm-none-eabi-gdb-py3'+suffix)), out=str(out/'runs'), stand=str(stand), tests=str(b))
(out/'session.json').write_text(json.dumps(session), encoding='utf-8')

from stm32_gdbtest.report_data import read, COLLECTIONS
import time
cases = {t['id']:t for t in collect([b])}
results=[]
reference={}
modes = [('compact','failures')] if a.storage_only else [('full','full'),('compact','failures')]
if a.summary:
    modes += [('full','summary'),('compact','summary')]
for representation, console in modes:
    api=out/(representation+'-'+console+'-api.toml')
    api.write_text('schema = 2\n[report]\nrepresentation = "'+representation+'"\nconsole = "'+console+'"\n',encoding='utf-8')
    config=out/(representation+'-'+console+'-session.toml')
    config.write_text('[config]\ntarget = '+json.dumps((b/'target.toml').as_posix())+'\napi = '+json.dumps(api.as_posix())+'\n[results]\ncapture = true\n',encoding='utf-8')
    session['session_config']=str(config)
    for name, expected in [('HW_REPORT_1000','PASS'),('HW_REPORT_10000','PASS'),('HW_REPORT_SWALLOWED','FAIL'),('HW_REPORT_LIVE','PASS'),('HW_REPORT_UNEXPECTED','FAIL'),('HW_REPORT_1000','PASS')] + ([('HW_REPORT_STORAGE','FAIL')] if representation=='compact' else []):
        if a.storage_only and name != 'HW_REPORT_STORAGE': continue
        start=time.perf_counter();code=run(session,cases[name]);elapsed=time.perf_counter()-start
        latest=sorted((out/'runs').glob('*/result.json'))[-1]
        result=read(latest)
        rows={key:result.get(key,[]) for key in COLLECTIONS}
        ok=result['status']==expected and result.get('cleanup')=='VERIFIED' and code==(2 if name=='HW_REPORT_STORAGE' else dict(PASS=0,FAIL=1,ERROR=2)[expected])
        if name in ('HW_REPORT_1000','HW_REPORT_10000','HW_REPORT_SWALLOWED'):
            if representation=='full':reference[name]=rows
            else:ok=ok and rows==reference[name]
        if name.startswith('HW_REPORT_1'):
            ok=ok and result['stops'][-1].get('frame')=='observe' and result['mutations'][-1].get('after')==2
        if representation=='compact':
            ok=ok and json.loads(latest.read_text(encoding='utf-8'))['report_schema']==2
            if name=='HW_REPORT_STORAGE':
                ok=ok and result.get('report_audit_error_count')==1 and bool(result.get('report_storage_error')) and 'primary storage control' in result.get('error','')
            log=(latest.parent/'gdb.log').read_text(encoding='utf-8',errors='replace')
            ok=ok and 'PASS sequence' not in log
        if console == 'summary':
            from stm32_gdbtest.report_summary import read as read_summary
            view = read_summary(latest)
            ok = ok and view['verdicts']['status'] == expected and view['collections']['checks']['total'] == len(result.get('checks', []))
            if name == 'HW_REPORT_SWALLOWED':
                ok = ok and view['collections']['checks']['failed'] == 1
            if name == 'HW_REPORT_STORAGE':
                ok = ok and view['analysis'] == 'partial'
            ok = ok and 'PASS sequence' not in (latest.parent/'gdb.log').read_text(encoding='utf-8', errors='replace')
        item=dict(case=name,console=console,representation=representation,status=result['status'],ok=ok,elapsed_s=elapsed,bytes=latest.stat().st_size,checks=len(result.get('checks',[])),result=str(latest.relative_to(out)))
        results.append(item)
        print(json.dumps(item),flush=True)
        (out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(out,flush=True)
raise SystemExit(0 if all(r['ok'] for r in results) else 1)
