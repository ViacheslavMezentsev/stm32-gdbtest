"""Fresh neutral ELF, sealed campaign, Renode probe and portable report in one command."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools import ddtt_coverage as core, ddtt_provenance as provenance, ddtt_report, renode_probe

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('gdb','renode','cxx'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--repository',default='ViacheslavMezentsev/stm32-gdbtest')
    p.add_argument('--negative-control',action='store_true')
    a=p.parse_args()
    if a.negative_control:
        os.environ['DDTT_NEGATIVE_CONTROL']='1'
    else:
        os.environ.pop('DDTT_NEGATIVE_CONTROL',None)
    out=ROOT/'build'/'renode-startup'/uuid.uuid4().hex
    out.mkdir(parents=True)
    base=ROOT/'tests/renode-startup'
    sha=provenance.git(ROOT,'rev-parse','HEAD').decode().strip()
    names=['tests/renode-startup/'+n for n in ('startup.cpp','startup.ld','platform.repl','scenario.py','map.template.json','run.py')]
    names += ['tools/'+n for n in ('renode_probe.py','ddtt_coverage.py','ddtt_guard.py','ddtt_provenance.py','ddtt_report.py','ddtt_view.py','ddtt_pages.css','ddtt_theme.js')]
    before=provenance.snapshot(ROOT,sha,names)
    elf=out/'startup.elf'
    with (out/'build.log').open('wb') as log:
        subprocess.run([a.cxx,'-mcpu=cortex-m3','-mthumb','-O0','-g3','-ffreestanding','-nostdlib',
            '-fno-exceptions','-fno-rtti','-fno-unwind-tables','-Wl,--build-id=none',
            '-T',str(base/'startup.ld'),str(base/'startup.cpp'),'-o',str(elf)],
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    if provenance.snapshot(ROOT,sha,names)!=before:
        raise ValueError('Build inputs changed')
    mapping=core.load(base/'map.template.json');mapping['elf_sha256']=core.digest(elf)
    for point in mapping['points']:
        point['source_sha256']=core.digest(ROOT/point['source'])
    (out/'map.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
    runs=out/'runs';runs.mkdir()
    provenance.begin(ROOT,sha,runs,out/'campaign.json',names,mapping)
    status=renode_probe.run(ROOT,elf,base/'platform.repl',base/'scenario.py',mapping,runs,
        a.gdb,a.renode,'EMU_STARTUP')
    provenance.seal(ROOT,runs,out/'campaign.json')
    report=ddtt_report.export(ROOT,mapping,runs,out/'campaign.json',a.repository,out/'public')
    print('Portable:',out/'public/index.html',report['summary'])
    return status

if __name__=='__main__':
    raise SystemExit(main())
