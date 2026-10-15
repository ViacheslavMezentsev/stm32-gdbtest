"""Run a bounded GDB-Python probe in an owned Renode instance (not a Target backend)."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import uuid
try:
    from .ddtt_coverage import digest, load, validate
except ImportError:
    from ddtt_coverage import digest, load, validate


def resc(path):
    text=Path(path).resolve().as_posix()
    if any(c in text for c in '\r\n"'):
        raise ValueError('Unsafe Renode path')
    return '@'+text.replace(' ', '\\ ')


def terminate(process):
    if process.poll() is None:
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10,check=True)
        else:
            os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=10)


def run(root,elf,model,scenario,mapping,runs,gdb,renode,case,timeout=30):
    root=Path(root).resolve()
    elf,model,scenario=map(lambda p:Path(p).resolve(),(elf,model,scenario))
    scenario_name=scenario.relative_to(root).as_posix()
    validate(mapping)
    if mapping.get('environment')!='emulator' or mapping['elf_sha256']!=digest(elf):
        raise ValueError('Expected emulator map for this ELF')
    inputs={p['source']:p['source_sha256'] for p in mapping['points']}
    for name,checksum in inputs.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or digest(path)!=checksum:
            raise ValueError('Stale source')
    preserved={p:digest(p) for p in (elf,model,scenario)}
    out=Path(runs)/('probe-'+uuid.uuid4().hex)
    out.mkdir(parents=True)
    started=datetime.now(timezone.utc).isoformat()
    result=dict(mode='emulator',purpose='automated',id=case,run_id=out.name,status='ERROR',
                started_utc=started,elf_sha256=digest(elf),checks=[],
                build_manifest={'inputs':[dict(file=k,sha256=v) for k,v in inputs.items()]})
    (out/'run.json').write_text(json.dumps({'test':{'path':str(scenario),'id':case}}),encoding='utf-8')
    process=None
    try:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        config=out/'renode.config'
        config.write_text('[general]\nuse-synchronous-logging = True\n',encoding='utf-8')
        script=out/'probe.resc'
        script.write_text('mach create "probe"\nmachine LoadPlatformDescription '+resc(model)
            +'\nsysbus LoadELF '+resc(elf)+f'\nmachine StartGdbServer {port}\n',encoding='utf-8')
        with (out/'renode.log').open('wb') as log:
            process=subprocess.Popen([renode,'--disable-gui','--console','--plain','--config',str(config),
                '--execute','include '+resc(script)],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=os.name!='nt')
            deadline=time.monotonic()+min(30,timeout)
            while b'GDB server with all CPUs started' not in (out/'renode.log').read_bytes():
                if process.poll() is not None or time.monotonic()>deadline:
                    raise TimeoutError('Renode readiness timeout')
                time.sleep(.05)
            gdbscript=out/'probe.gdb'
            gdbscript.write_text('set pagination off\nset confirm off\nset remotetimeout 10\n'
                +f'target remote 127.0.0.1:{port}\npython\n'
                +f'exec(compile(open({str(scenario)!r}, encoding="utf-8-sig").read(), {str(scenario)!r}, "exec"))\n'
                +'end\ndisconnect\n',encoding='utf-8')
            env=os.environ.copy()
            for key in ('PYTHONHOME','PYTHONPATH'):
                env.pop(key,None)
            env['PYTHONDONTWRITEBYTECODE']='1'
            env['DDTT_PROBE_RESULT']=str((out/'checks.json').resolve())
            with (out/'gdb.log').open('wb') as log:
                done=subprocess.run([gdb,'-nx','-nh','-batch','-iex','set auto-load off',str(elf),'-x',str(gdbscript)],
                    env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            report=load(out/'checks.json')
            if done.returncode or report.get('status') not in ('PASS','FAIL'):
                raise RuntimeError('GDB probe incomplete')
            checks=report['checks']
            if not checks or any(not isinstance(c.get('name'),str) or type(c.get('passed')) is not bool for c in checks):
                raise ValueError('Invalid probe checks')
            if any(digest(p)!=h for p,h in preserved.items()) or any(digest(root/n)!=h for n,h in inputs.items()):
                raise ValueError('Inputs changed during probe')
            expected_status='PASS' if all(c['passed'] for c in checks) else 'FAIL'
            if report['status'] != expected_status:
                raise ValueError('Probe status contradicts checks')
            result['checks']=checks
            result['status']='PASS' if all(c['passed'] for c in checks) else 'FAIL'
    except Exception as error:
        result['error']=str(error)
    finally:
        try:
            if process is not None:
                terminate(process)
                with socket.socket() as released:
                    released.bind(('127.0.0.1',port))
            result['cleanup']='VERIFIED'
        except Exception as error:
            result['cleanup']='ERROR';result['cleanup_error']=str(error);result['status']='ERROR'
        (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(result['status'],out/'result.json')
    return 0 if result['status']=='PASS' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('project','elf','model','scenario','map','runs','gdb','renode','case'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--timeout',type=float,default=30)
    a=p.parse_args()
    if not 0<a.timeout<=300:
        p.error('timeout must be in (0, 300]')
    return run(a.project,a.elf,a.model,a.scenario,load(a.map),a.runs,a.gdb,a.renode,a.case,a.timeout)

if __name__=='__main__':
    raise SystemExit(main())
