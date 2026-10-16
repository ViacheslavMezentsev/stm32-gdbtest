"""Real Target contracts on a disposable neutral ELF; no hardware access."""
import json
import os
from pathlib import Path
import sys
import gdb
sys.path.insert(0, os.environ['DDTT_MODULE_ROOT'])
from stm32_gdbtest.target import Target
from stm32_gdbtest import ApiError
report={'checks':[]}
t=Target(report,{'flash_start':0x08000000,'flash_size':65536})
# Stop before installing Target's stop listener: its runner context is intentionally absent.
gdb.events.stop.disconnect(t.on_stop)
status='ERROR'
try:
    gdb.Breakpoint('ready',temporary=True,internal=True)
    gdb.execute('continue')
    pc=int(gdb.parse_and_eval('$pc'));sp=int(gdb.parse_and_eval('$sp'))
    address=int(gdb.parse_and_eval('&counter'))
    saved=t.memory(address,4)
    t.check('memory snapshot',len(saved),4)
    t.check('memory matches direct read',saved.hex(),bytes(gdb.selected_inferior().read_memory(address,4)).hex())
    for verify in (True,False):
        for function,expected in [('next_value',1),('constant_value',42)]:
            gdb.execute('set variable rhs_calls = 0')
            result=t.write('receiver',function+'()',verify=verify)
            t.check(f'{function} verify={verify} calls',t.read('rhs_calls'),1)
            t.check(f'{function} verify={verify} value',t.read('receiver'),expected)
            t.check(f'{function} verify={verify} flag',result['verified'],verify)
        gdb.execute('set variable rhs_calls = 0')
        t.write([('receiver','next_value()'),('receiver','next_value()')],verify=verify)
        t.check(f'rows verify={verify} calls',t.read('rhs_calls'),2)
        t.check(f'rows verify={verify} value',t.read('receiver'),2)
    for path,rhs,expected in [('small_signed','255',-1),('small_unsigned',257,1),('float_value',1.25,1.25),('bool_value',2,True),('wide_value','0x123456789abcdef0ULL',0x123456789abcdef0),('counter_pointer','&counter',address),('mode_value','MODE_RUN',1)]:
        result=t.write(path,rhs)
        t.check('converted '+path,t.read(path),expected)
        t.check('verified '+path,result['verified'],True)
    gdb.execute('set variable rhs_calls = 0')
    value=t.evaluate('next_value()',as_type=int)
    t.write('receiver',value)
    t.check('ready value no extra calls',t.read('rhs_calls'),1)
    try:
        t.write('receiver','missing_rhs()')
    except ApiError as error:
        t.check('failed RHS code',error.code,'command_failed')
        t.check('failed RHS effect',error.details['effect'],'unknown')
    else:
        t.check('failed RHS rejected',False,True)
    t.check('context PC restored',int(gdb.parse_and_eval('$pc')),pc)
    t.check('context SP restored',int(gdb.parse_and_eval('$sp')),sp)
    t.check('neighbor object preserved',t.memory(address,4).hex(),saved.hex())
    status='PASS'
except Exception:
    status='FAIL' if any(not c['passed'] for c in report['checks']) else 'ERROR'
    raise
finally:
    Path(os.environ['DDTT_PROBE_RESULT']).write_text(json.dumps(dict(status=status,checks=report['checks'])),encoding='utf-8')
