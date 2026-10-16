"""Build and exercise the real runner; results stay under build/qemu-backend."""
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
p.add_argument('--qemu', required=True)
a = p.parse_args()
b = Path(__file__).resolve().parent
out = ROOT / 'build/qemu-backend' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out.mkdir(parents=True)
suffix = '.exe' if sys.platform == 'win32' else ''
bin = a.toolchain / 'bin'
elf = out / 'firmware.elf'
cmd = [str(bin / ('arm-none-eabi-g++' + suffix)), '-mcpu=cortex-m4', '-mthumb', '-O0', '-g3', '-nostdlib', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-Wl,--build-id=none', '-T', str(b.parent/'renode-backend/startup.ld'), str(b/'startup.cpp'), '-o', str(elf)]
subprocess.run(cmd, check=True)
stand = out / 'stand.toml'
stand.write_text((b/'stand.example.toml').read_text().replace('executable = "qemu-system-arm"', 'executable = '+json.dumps(Path(a.qemu).as_posix())), encoding='utf-8')
session = dict(root=str(ROOT), elf=str(elf), profile=str(b/'target.toml'), session_config=str(b/'session.toml'), gdb=str(bin/('arm-none-eabi-gdb-py3'+suffix)), out=str(out/'runs'), stand=str(stand), tests=str(b.parent/'renode-backend'))
(out/'session.json').write_text(json.dumps(session), encoding='utf-8')
cases = {t['id']:t for t in collect([b.parent/'renode-backend'])}
results = []
if run(session, cases['HW_EMU_STARTUP'], prepare_only=True) != 0:
    raise SystemExit('Preparation failed')
for name, expected in [('HW_EMU_STARTUP','PASS'),('HW_EMU_FAIL','FAIL'),('HW_EMU_RESET','PASS'),('HW_EMU_TIMEOUT','ERROR'),('HW_EMU_STARTUP','PASS')]:
    code = run(session,cases[name])
    latest = sorted((out/'runs').glob('*/result.json'))[-1]
    result = json.loads(latest.read_text())
    ok = result['status']==expected and result.get('cleanup')=='VERIFIED' and result['mode']=='emulator'
    if expected=='PASS':ok = ok and code==0 and result.get('image_verified') is True and result.get('capture',{}).get('status')=='saved'
    results.append(dict(case=name,expected=expected,status=result['status'],ok=ok,result=str(latest.relative_to(ROOT))))
# A process that exits before the GDB listener must never become scenario PASS.
bad_stand = out/'early-exit.toml'
bad_stand.write_text(stand.read_text().replace(json.dumps(Path(a.qemu).as_posix()), json.dumps(Path(sys.executable).as_posix())), encoding='utf-8')
run(session, cases['HW_EMU_STARTUP'], stand_path=str(bad_stand))
latest = sorted((out/'runs').glob('*/result.json'))[-1]
result = json.loads(latest.read_text())
results.append(dict(case='early-exit', expected='ERROR', status=result['status'],
                    ok=result['status']=='ERROR' and result.get('cleanup')=='VERIFIED' and not result.get('connection_attempted'),
                    result=str(latest.relative_to(ROOT))))
# Opt-in semihosting must actually emit the witness through QEMU, not through GDB.
semi = out/'semihosting.toml'
semi.write_text(stand.read_text().replace('semihosting = false','semihosting = true'), encoding='utf-8')
semi_elf = out/'semihosting.elf'
subprocess.run(cmd[:-2]+['-DQA_SEMIHOSTING=1','-o',str(semi_elf)],check=True)
code=run(dict(session,elf=str(semi_elf)),cases['HW_EMU_STARTUP'],stand_path=str(semi))
latest=sorted((out/'runs').glob('*/result.json'))[-1]
result=json.loads(latest.read_text())
results.append(dict(case='semihosting-enabled',expected='PASS',status=result['status'],
                    ok=code==0 and result['status']=='PASS' and result.get('cleanup')=='VERIFIED'
                    and 'QEMU semihosting witness' in latest.with_name('server.log').read_text(errors='replace'),
                    result=str(latest.relative_to(ROOT))))
(out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
raise SystemExit(0 if all(r['ok'] for r in results) else 1)
