"""Build and run the C++ preflight and runtime regression in Renode."""
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
    base=ROOT/'tests/renode-startup';out=ROOT/'build/cpp-preflight'/uuid.uuid4().hex
    out.mkdir(parents=True)
    elf=out/'contracts.elf'
    command=[a.cxx,'-mcpu=cortex-m3','-mthumb','-O0','-g3','-ffreestanding','-nostdlib','-fno-exceptions','-fno-rtti','-fno-unwind-tables','-Wl,--build-id=none','-T',str(base/'startup.ld'),str(base/'cpp_contracts.cpp'),'-o',str(elf)]
    inputs=[base/'cpp_contracts.cpp',base/'startup.ld',base/'platform.repl',base/'scenario_cpp.py',Path(__file__).resolve(),*sorted((Path(a.module_root)/'stm32_gdbtest').glob('*.py'))]
    hashes={str(p.resolve()):core.digest(p) for p in inputs}
    (out/'inputs.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    (out/'build-command.json').write_text(json.dumps(command),encoding='utf-8')
    with (out/'build.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    os.environ['DDTT_MODULE_ROOT']=str(Path(a.module_root).resolve())
    os.environ['DDTT_CPP_OFFLINE']='1'
    os.environ['DDTT_PROBE_RESULT']=str(out.resolve()/'offline.json')
    script=out/'offline.gdb'
    script.write_text('python\nexec(compile(open('+repr(str((base/'scenario_cpp.py').resolve()))+", encoding='utf-8').read(), 'scenario_cpp.py', 'exec'))\nend\n",encoding='utf-8')
    with (out/'offline.log').open('wb') as log:
        process=subprocess.run([a.gdb,'-nx','-nh','-batch','-iex','set auto-load off',str(elf),'-x',str(script)],stdout=log,stderr=subprocess.STDOUT,timeout=30)
    offline=json.loads((out/'offline.json').read_text())
    print('Offline:',offline['status'],len(offline['checks']),out,flush=True)
    if process.returncode or offline['status']!='PASS':return 1
    os.environ.pop('DDTT_CPP_OFFLINE',None)
    mapping=dict(schema=1,environment='emulator',elf_sha256=core.digest(elf),points=[dict(source='tests/renode-startup/cpp_contracts.cpp',source_sha256=core.digest(base/'cpp_contracts.cpp'),anchor='probe.value = 3;',scenario='CPP_PREFLIGHT',check='object initialized')])
    code=renode_probe.run(ROOT,elf,base/'platform.repl',base/'scenario_cpp.py',mapping,out/'runs',a.gdb,a.renode,'CPP_PREFLIGHT',60)
    if any(core.digest(Path(n))!=h for n,h in hashes.items()):raise RuntimeError('Inputs changed')
    return code
if __name__=='__main__':raise SystemExit(main())
