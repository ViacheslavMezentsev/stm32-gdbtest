"""F411 opt-in campaign; the default route only prints a plan."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
from prepare import B, ROOT
from sealed import validate
from transport import phase, save, tool, server_commands
from run import assess

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--stand', type=Path, required=True)
    p.add_argument('--serial', required=True)
    p.add_argument('--allow-hardware', choices=['f411ce'])
    p.add_argument('--admission', type=Path)
    p.add_argument('--recover', type=Path)
    p.add_argument('--events', type=Path)
    a = p.parse_args()
    bundle = a.package.resolve()
    m = validate(bundle)
    sys.path.insert(0, str(ROOT))
    from stm32_gdbtest.backends import load_stand
    stand = load_stand(a.stand)
    if stand['backend'] != 'openocd' or stand.get('remote') or stand.get('serial') != a.serial or 'stlink' not in stand.get('interface', ''):
        raise ValueError('exact local ST-Link/OpenOCD required')
    profile = tomllib.loads((B / 'hardware-target.toml').read_text())
    if not a.allow_hardware:
        print(json.dumps(dict(hardware='NOT_RUN', cases=m['cases'], server=server_commands(stand, profile, 3333, bundle)['command']), indent=2))
        return
    admission = json.loads(a.admission.read_text()) if a.admission else {}
    if admission.get('serial') != a.serial or admission.get('elf_sha256') != m['files']['neutral.elf'] or any((admission.get(k) is not True for k in ('stand_free', 'watchdog_inactive', 'loads_disconnected', 'reset_resume_allowed'))):
        raise ValueError('fresh explicit admission required')
    attempt = bundle / ('hardware-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    attempt.mkdir()
    g = dict(flash_size=m['flash_size'], ram_size=m['ram_size'], sector=m['sector'], cpu='cortex-m4', serial=a.serial, flash_size_address=0x1fff7a22, elf_sha256=m['files']['neutral.elf'], bin_sha256=m['files']['neutral.bin'])
    backup = a.recover.resolve() if a.recover else attempt / 'backup'
    events = a.events.resolve() if a.events else attempt / 'fpb-events.jsonl'

    def step(action, image=None):
        return phase(action, attempt / (action + '-phase'), backup, stand, profile, g, m['toolchain'], image, p4_package=bundle, p4_events=events)
    if a.recover:
        step('recover')
        return
    step('backup')
    rows = []
    error = None
    try:
        step('load', bundle / 'neutral.elf')
        for name in ('hook.bin', 'symbols.json'):
            shutil.copy2(bundle / name, attempt / name)
        os.environ['LIVE_OBSERVER_BUNDLE'] = str(attempt)
        raw = tomllib.loads(a.stand.read_text())['probe']
        raw['flash'] = 'verify-only'
        local = attempt / 'stand.toml'
        local.write_text('[probe]\n' + '\n'.join((k + ' = ' + json.dumps(v) for k, v in raw.items())))
        from stm32_gdbtest.collect import collect
        from stm32_gdbtest.runner import run
        session = dict(root=str(ROOT), elf=str(bundle / 'neutral.elf'), profile=str(B / 'hardware-target.toml'), session_config=str(B / 'hardware-session.toml'), gdb=tool(m['toolchain'], 'gdb-py3'), out=str(attempt / 'runs'), stand=str(local), tests=str(B), identity_policy='strict')
        for c in collect([B]):
            code = run(session, c)
            path = sorted((attempt / 'runs').glob('*/result.json'))[-1]
            result = json.loads(path.read_text())
            records = json.loads((path.parent / 'records.json').read_text())['records']
            row = assess(c['id'], result, records, code)
            row['result'] = str(path)
            ok = row['ok']
            rows.append(row)
            save(attempt / 'summary.json', rows)
            if not ok:
                raise RuntimeError('unexpected result; recovery before further tests')
    except BaseException as e:
        error = repr(e)
        raise
    finally:
        try:
            step('recover')
        finally:
            save(attempt / 'campaign.json', dict(body_error=error, complete=len(rows) == len(m['cases']) and all((r['ok'] for r in rows)), hardware='RUN', recovery_report=str(backup / 'recovery.json')))
if __name__ == '__main__':
    main()
