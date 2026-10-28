"""Offline ELF contracts and live calls are deliberately separate evidence."""
import json
import os
from pathlib import Path
import sys
import gdb
sys.path.insert(0, os.environ['DDTT_MODULE_ROOT'])
from stm32_gdbtest.contracts import inspect_contracts
from stm32_gdbtest.target import Target
from stm32_gdbtest import ApiError

checks = []
def check(name, actual, expected):
    checks.append(dict(name=name, actual=actual, expected=expected, passed=actual == expected))
    if actual != expected:
        raise AssertionError(name + ': ' + repr(actual))

def contract(symbol, returns, arguments):
    return dict(type_context=symbol, functions={symbol: dict(returns=returns,
        arguments=[dict(name=n, type=t) for n, t in arguments])})

contracts = {
    'method': contract('Probe::add', 'void', [('this', 'Probe * const'), ('n', 'unsigned int')]),
    'const_method': contract('Probe::read', 'unsigned int', [('this', 'const Probe * const')]),
    'static': contract('Probe::twice', 'unsigned int', [('n', 'unsigned int')]),
    'namespace': contract('demo::increment', 'unsigned int', [('n', 'unsigned int')]),
    'free_cpp': contract('free_cpp', 'unsigned int', [('n', 'unsigned int')]),
    'void': contract('set_value', 'void', [('n', 'unsigned int')]),
}
status = 'ERROR'
try:
    offline = os.environ.get('DDTT_CPP_OFFLINE') == '1'
    if offline:
        check('no inferior before preflight', gdb.selected_inferior().pid, 0)
    results = {}
    for name, spec in contracts.items():
        result = inspect_contracts(gdb, dict(contracts={name: spec}))
        results[name] = result
        check('preflight ' + name, result['status'], 'PASS')
    for name, spec, fragment in [
        ('wrong_this', contract('Probe::add', 'void', [('this', 'const Probe *'), ('n', 'unsigned int')]), 'argument 0'),
        ('unqualified_this', contract('Probe::add', 'void', [('this', 'Probe *'), ('n', 'unsigned int')]), 'argument 0'),
        ('wrong_const_method', contract('Probe::read', 'unsigned int', [('this', 'Probe * const')]), 'argument 0'),
        ('bad_return', contract('Probe::twice', 'void', [('n', 'unsigned int')]), 'return'),
        ('bad_arity', contract('Probe::twice', 'unsigned int', []), 'arity'),
        ('absent_inline', contract('Probe::absent', 'unsigned int', []), 'Function absent'),
    ]:
        result = inspect_contracts(gdb, dict(contracts={name: spec}))
        results[name] = result
        check('preflight rejects ' + name, result['status'], 'ERROR')
        check('preflight reason ' + name, fragment in result['errors'][0]['error'], True)
    Path(os.environ['DDTT_PROBE_RESULT']).with_suffix('.contracts.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    if offline:
        check('no inferior after preflight', gdb.selected_inferior().pid, 0)
    else:
        gdb.Breakpoint('ready', temporary=True, internal=True)
        gdb.execute('continue')
        t = Target({'checks': []}, {'flash_start': 0x08000000, 'flash_size': 65536})
        gdb.events.stop.disconnect(t.on_stop)
        pc = int(gdb.parse_and_eval('$pc')); sp = int(gdb.parse_and_eval('$sp'))
        address = int(gdb.parse_and_eval('&probe'))
        saved = bytes(gdb.selected_inferior().read_memory(address, gdb.lookup_type('Probe').sizeof))
        try:
            check('object initialized', int(gdb.parse_and_eval('probe.value')), 3)
            gdb.parse_and_eval('probe.add(5)')
            check('method effect', int(gdb.parse_and_eval('probe.value')), 8)
            check('const method result', int(gdb.parse_and_eval('probe.read()')), 8)
            check('static method result', int(gdb.parse_and_eval('Probe::twice(6)')), 12)
            check('namespace result', int(gdb.parse_and_eval('demo::increment(6)')), 7)
            check('Target free C++', t.call('free_cpp', 4)['return_value'], 6)
            check('Target void', t.call('set_value', 12)['return_value'], None)
            check('void effect', int(gdb.parse_and_eval('probe.value')), 12)
            check('Target static', t.call('Probe::twice', 6)['return_value'], 12)
            check('Target namespace', t.call('demo::increment', 6)['return_value'], 7)
            for symbol in ('probe.add',):
                try:
                    t.call(symbol, 1)
                except ApiError as error:
                    check('Target rejects ' + symbol, error.code, 'invalid_function')
                else:
                    check('Target rejects ' + symbol, 'accepted', 'invalid_function')
        finally:
            gdb.selected_inferior().write_memory(address, saved)
            check('object restored', bytes(gdb.selected_inferior().read_memory(address, len(saved))).hex(), saved.hex())
            check('PC restored', int(gdb.parse_and_eval('$pc')), pc)
            check('SP restored', int(gdb.parse_and_eval('$sp')), sp)
    status = 'PASS'
except Exception:
    status = 'FAIL' if any(not c['passed'] for c in checks) else 'ERROR'
    raise
finally:
    Path(os.environ['DDTT_PROBE_RESULT']).write_text(json.dumps(dict(status=status, checks=checks)), encoding='utf-8')
