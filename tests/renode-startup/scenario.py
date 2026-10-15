"""Executed only by GDB's main Python thread in a disposable emulator."""
import json
import os
import gdb
checks=[]
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
try:
    gdb.Breakpoint('ready',temporary=True,internal=True)
    gdb.execute('continue')
    check('startup completed',int(gdb.parse_and_eval('started'))==1)
    check('counter initialized',int(gdb.parse_and_eval('counter.value'))==3)
    gdb.execute('call counter.add(4)')
    check('method updated object',int(gdb.parse_and_eval('counter.value'))==(8 if os.environ.get('DDTT_NEGATIVE_CONTROL')=='1' else 7))
    status='PASS' if all(c['passed'] for c in checks) else 'FAIL'
except Exception:
    status='ERROR'
    raise
finally:
    with open(os.environ['DDTT_PROBE_RESULT'],'w',encoding='utf-8') as stream:
        json.dump(dict(status=status,checks=checks),stream)
