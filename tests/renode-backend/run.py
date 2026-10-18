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
out = ROOT / 'build/renode-backend' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
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
cases = {t['id']:t for t in collect([b])}
results = []
if run(session, cases['HW_EMU_STARTUP'], prepare_only=True) != 0:
    raise SystemExit('Preparation failed')
for name, expected in [('HW_EMU_STARTUP','PASS'),('HW_EMU_FAIL','FAIL'),('HW_EMU_RESET','PASS'),('HW_EMU_TIMEOUT','ERROR'),('HW_EMU_STARTUP','PASS'),('HW_EMU_LIVE','PASS'),('HW_EMU_LIVE_ERROR','ERROR'),('HW_EMU_LIVE_FAULT','ERROR'),('HW_EMU_LIVE_SKIP','SKIP'),('HW_EMU_LIVE_FAIL','FAIL'),('HW_EMU_LIVE_RETURN','PASS'),('HW_EMU_SYNC_REFUSAL','PASS'),('HW_EMU_LIVE','PASS')]:
    code = run(session,cases[name])
    latest = sorted((out/'runs').glob('*/result.json'))[-1]
    result = json.loads(latest.read_text())
    ok = result['status']==expected and result.get('cleanup')=='VERIFIED' and result['mode']=='emulator'
    if name.startswith('HW_EMU_LIVE'):ok = ok and result.get('execution_cleanup')=='VERIFIED'
    if expected=='PASS':ok = ok and code==0 and result.get('image_verified') is True and result.get('capture',{}).get('status')=='saved'
    results.append(dict(case=name,expected=expected,status=result['status'],ok=ok,result=str(latest.relative_to(ROOT))))
# Invalid platform must time out before any scenario; owned process is still reaped.
bad_platform = out/'invalid.repl'
bad_platform.write_text('invalid platform syntax', encoding='utf-8')
bad_stand = out/'invalid.toml'
bad_stand.write_text(stand.read_text().replace((b/'platform.repl').as_posix(), bad_platform.as_posix()).replace('startup_timeout_s = 15', 'startup_timeout_s = 2'), encoding='utf-8')
run(session, cases['HW_EMU_STARTUP'], stand_path=str(bad_stand))
latest = sorted((out/'runs').glob('*/result.json'))[-1]
result = json.loads(latest.read_text())
results.append(dict(case='invalid-platform',expected='ERROR',status=result['status'],
                    ok=result['status']=='ERROR' and result.get('cleanup')=='VERIFIED' and not result.get('connection_attempted'),
                    result=str(latest.relative_to(ROOT))))
(out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
raise SystemExit(0 if all(r['ok'] for r in results) else 1)
