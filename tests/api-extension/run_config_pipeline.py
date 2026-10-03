"""Explicit local M4 experiment with real ELF/GDB-Python, never a target connection."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from session_pipeline import open_configured, prepare_and_pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    args = parser.parse_args()
    session = json.loads(args.session.read_text(encoding='utf-8'))
    output = HERE / 'build' / ('pipeline-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir(parents=True)
    source = output / 'source'
    source.mkdir()
    original_profile = Path(session['profile'])
    shutil.copyfile(original_profile, source / 'target.toml')
    shutil.copyfile(original_profile.parent/'full-image.toml', source/'image.toml')
    (source/'api.toml').write_text('schema=1\n[records]\nmax_records=7\n'
        '[measurement]\nsamples=3\nday=2026-10-03\n', encoding='utf-8')
    (source/'session.toml').write_text('[config]\ntarget="target.toml"\n'
        'api="api.toml"\nimage="image.toml"', encoding='utf-8')
    session.update(profile=str(source/'target.toml'), session_config=str(source/'session.toml'))
    summary = {'status':'ERROR', 'hardware':False}
    try:
        summary['prepare'] = prepare_and_pack(session, output/'package.zip', ['HW_CI_ADC_UNITS'])
        # Keep evidence but invalidate all original configuration paths.
        source.rename(output/'source-moved')
        restored, snapshot = open_configured(output/'package.zip', output/'receiver', session['gdb'])
        result_path = output/'gdb-config.json'
        script = output/'scenario.gdb'
        python = f'''import sys, json, traceback
sys.path.insert(0, {str(HERE.parents[1])!r})
sys.path.insert(0, {str(HERE)!r})
from pathlib import Path
from datetime import date
from config_transport import loads
from session_pipeline import ConfiguredTarget
from stm32_gdbtest.target import Target
from evidence import Journal
report = {{"checks": [], "status": "ERROR", "connection_attempted": False}}
target = None
try:
    snapshot = loads(Path({str(Path(restored['root'])/'research/config.json')!r}).read_text(encoding="utf-8"))
    target = Target(report, snapshot.config["target"])
    t = ConfiguredTarget(target, snapshot)
    t.check("packaged MCU", t.config["target"]["mcu"], {snapshot.config['target']['mcu']!r})
    t.check("custom parameter", t.config["api"]["measurement"]["samples"], 3)
    t.check("TOML date preserved", type(t.config["api"]["measurement"]["day"]) is date, True)
    t.check("raw has no defaults", "max_depth" in t.config_props["api"]["data"]["records"], False)
    t.check("effective has defaults", t.config["api"]["records"]["max_depth"], 8)
    journal = Journal(**dict(t.config["api"]["records"]))
    journal.record("sample", {{"value": 3300}})
    t.check("configured journal", journal.records()[0]["data"]["value"], 3300)
    report["status"] = "PASS"
except BaseException:
    report["error"] = traceback.format_exc()
finally:
    if target is not None:
        target.close()
    Path({str(result_path)!r}).write_text(json.dumps(report, indent=2), encoding="utf-8")
'''
        script.write_text('set pagination off\nset confirm off\npython\n'+python+'\nend\nquit\n', encoding='utf-8')
        with (output/'gdb.log').open('w', encoding='utf-8') as log:
            completed = subprocess.run([session['gdb'], '-nx','-batch','-q','-iex',
                                        'set auto-load off','-x',str(script)], cwd=output/'receiver',
                                       stdout=log, stderr=subprocess.STDOUT, timeout=30)
        summary['gdb'] = json.loads(result_path.read_text(encoding='utf-8'))
        if completed.returncode or summary['gdb']['status'] != 'PASS':
            raise RuntimeError('GDB configuration scenario failed')
        summary['status'] = 'PASS'
    finally:
        (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(output/'summary.json')


if __name__ == '__main__':
    main()
