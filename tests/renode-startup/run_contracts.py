"""Build and run the memory/write contract regression in Renode."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools import ddtt_coverage as core, renode_probe

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('gdb','cxx','renode'):p.add_argument('--'+key,required=True)
    p.add_argument('--module-root',default=str(ROOT),help='Optional baseline checkout for before/after comparison')
    a=p.parse_args()
    base=ROOT/'tests/renode-startup';out=ROOT/'build/memory-write'/uuid.uuid4().hex
    out.mkdir(parents=True)
    elf=out/'contracts.elf'
    command=[a.cxx,'-mcpu=cortex-m3','-mthumb','-O0','-g3','-ffreestanding','-nostdlib','-fno-exceptions','-fno-rtti','-fno-unwind-tables','-Wl,--build-id=none','-T',str(base/'startup.ld'),str(base/'startup.cpp'),'-o',str(elf)]
    inputs=[base/'startup.cpp',base/'startup.ld',base/'platform.repl',base/'scenario_contracts.py',Path(__file__).resolve(),*sorted((Path(a.module_root)/'stm32_gdbtest').glob('*.py'))]
    hashes={str(p.resolve()):core.digest(p) for p in inputs}
    (out/'inputs.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    (out/'build-command.json').write_text(json.dumps(command),encoding='utf-8')
    with (out/'build.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    os.environ['DDTT_MODULE_ROOT']=str(Path(a.module_root).resolve())
    mapping=dict(schema=1,environment='emulator',elf_sha256=core.digest(elf),points=[dict(source='tests/renode-startup/startup.cpp',source_sha256=core.digest(base/'startup.cpp'),anchor='counter.value = 0;',scenario='API_MEMORY_WRITE',check='memory snapshot')])
    code=renode_probe.run(ROOT,elf,base/'platform.repl',base/'scenario_contracts.py',mapping,out/'runs',a.gdb,a.renode,'API_MEMORY_WRITE',60)
    if any(core.digest(Path(n))!=h for n,h in hashes.items()):raise RuntimeError('Inputs changed')
    return code
if __name__=='__main__':raise SystemExit(main())
