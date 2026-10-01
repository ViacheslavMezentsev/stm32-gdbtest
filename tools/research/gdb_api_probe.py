"""Read-only rc3 capability inventory; run in a clean batch GDB without a target.

Attribute presence is L0 evidence only, not proof of hardware support.
This script never connects, loads firmware, resumes, or accesses target memory.
"""

import json
import sys
import gdb

names = (
    'Value.is_unavailable', 'Value.bytes', 'Value.assign', 'Value.fetch_lazy',
    'Value.string', 'Value.cast', 'Frame.read_var', 'Frame.read_register',
    'Frame.older', 'Frame.is_valid', 'Frame.architecture', 'Breakpoint.locations',
    'FinishBreakpoint', 'FinishBreakpoint.return_value', 'Inferior.read_memory',
    'Inferior.write_memory', 'Inferior.search_memory', 'Architecture.disassemble',
    'events.stop', 'events.cont', 'events.memory_changed', 'events.inferior_call',
    'post_event', 'interrupt', 'Thread', 'blocked_signals', 'with_parameter',
)
checks = {}
for name in names:
    obj = gdb
    for part in name.split('.'):
        obj = getattr(obj, part, None)
    checks[name] = obj is not None
parameters = {}
for name in ('may-call-functions', 'direct-call-timeout', 'indirect-call-timeout',
             'unwind-on-timeout', 'unwindonsignal', 'non-stop', 'can-use-hw-watchpoints'):
    try:
        parameters[name] = gdb.parameter(name)
    except Exception as exc:
        parameters[name] = {'unavailable': str(exc)}
print('RC3_PROBE=' + json.dumps({'gdb': gdb.VERSION, 'python': sys.version.split()[0],
    'hardware_accessed': False, 'api_presence': checks, 'parameters': parameters,
    'value_conversion': {'int_3_5': int(gdb.Value(3.5)), 'float_3_5': float(gdb.Value(3.5))}}, sort_keys=True))
