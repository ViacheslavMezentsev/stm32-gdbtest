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
a = p.parse_args()
b = Path(__file__).resolve().parent
out = ROOT / 'build/report-quota-renode' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out.mkdir(parents=True)
suffix = '.exe' if sys.platform == 'win32' else ''
bin = a.toolchain / 'bin'
elf = out / 'firmware.elf'
cmd = [str(bin / ('arm-none-eabi-g++' + suffix)), '-mcpu=cortex-m3', '-mthumb', '-O0', '-g3', '-nostdlib', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none', '-T', str(b/'startup.ld'), str(b/'startup.cpp'), '-o', str(elf)]
subprocess.run(cmd, check=True)
platform=out/'platform.repl'
platform.write_text((b/'platform.repl').read_text(encoding='utf-8') + '\nmmio: Memory.MappedMemory @ sysbus 0x40000000\n    size: 0x1000\n',encoding='utf-8')
stand = out / 'stand.toml'
stand.write_text((b/'stand.example.toml').read_text().replace('executable = "renode"', 'executable = '+json.dumps(Path(a.renode).as_posix())).replace('"platform.repl"', json.dumps(platform.as_posix())), encoding='utf-8')
session = dict(root=str(ROOT), elf=str(elf), profile=str(b/'target.toml'), session_config=str(b/'session.toml'), gdb=str(bin/('arm-none-eabi-gdb-py3'+suffix)), out=str(out/'runs'), stand=str(stand), tests=str(b))
(out/'session.json').write_text(json.dumps(session), encoding='utf-8')

from stm32_gdbtest.report_data import read
from stm32_gdbtest.result_capture import read as read_capture
from stm32_gdbtest.report_summary import read as read_summary
cases={t['id']:t for t in collect([b])}
results=[]
for representation in ('full','compact'):
    for report_policy in ('error','truncate'):
        for journal_policy in ('error','truncate'):
            stem=representation+'-'+report_policy+'-'+journal_policy
            api=out/(stem+'-api.toml')
            api.write_text('schema=3\n[records]\nmax_records=4\n[journal]\nrepresentation="'+representation+'"\non_limit="'+journal_policy+'"\n[report]\nrepresentation="'+representation+'"\nconsole="summary"\non_limit="'+report_policy+'"\nmax_rows_per_collection=4\n',encoding='utf-8')
            config=out/(stem+'-session.toml')
            config.write_text('[config]\ntarget='+json.dumps((b/'target.toml').as_posix())+'\napi='+json.dumps(api.as_posix())+'\n[results]\ncapture=true\n',encoding='utf-8')
            session['session_config']=str(config)
            for suffix_case in ('PASS','FAIL','MIXED','LIVE'):
                name='HW_REPORT_QUOTA_'+suffix_case
                expected='FAIL' if suffix_case=='FAIL' else 'PASS'
                # Live operations also exhaust the independent journal quota.
                if report_policy=='error' or (journal_policy=='error' and suffix_case in ('MIXED','LIVE')):
                    expected='ERROR'
                code=run(session,cases[name])
                latest=sorted((out/'runs').glob('*/result.json'))[-1]
                result=read(latest);capture=read_capture(latest.parent,result);summary=read_summary(latest)
                meta=result['evidence']['stores']['checks']
                ok=(code==2 and result['status']==expected and result.get('cleanup')=='VERIFIED'
                    and result['capture']['status']=='saved' and len(result['checks'])==4
                    and meta['state']==('truncated' if report_policy=='truncate' else 'unavailable')
                    and summary['analysis']=='partial')
                if report_policy=='truncate' and suffix_case=='FAIL':
                    ok=ok and result['check_accounting']['failed']==1 and all(x['passed'] for x in result['checks'])
                if report_policy=='truncate' and suffix_case=='LIVE' and journal_policy=='truncate':
                    ok=ok and result['evidence']['stores']['stops']['state']=='truncated'
                item=dict(case=name,report_policy=report_policy,journal_policy=journal_policy,
                    representation=representation,status=result['status'],ok=ok,result=str(latest.relative_to(out)))
                results.append(item);print(json.dumps(item),flush=True)
                (out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(out,flush=True)
raise SystemExit(0 if all(x['ok'] for x in results) else 1)
