"""E4 scalar/void return, foreign stop and capacity on unchanged CMSIS F411."""

from dataclasses import asdict
from stm32_gdbtest import case
from natural_finish import CortexMBackend, FinishError, finish


@case('HW_E4_FINISH', contracts=('ci_app_api',))
def exercise(t):
    backend = CortexMBackend(t)
    guards = [bp.number for bp in t.owned if bp.is_valid()]
    evidence = []
    t.reach('app_step')
    expected = t.value('state->ticks') + 1
    result = finish(backend)
    evidence.append(asdict(result))
    t.check('natural scalar return', (result.outcome,result.value_state,result.value),
            ('returned','available',expected))
    t.reach('board_led_toggle')
    t.check('caller published value', t.value('app_state.ticks'), expected)
    result = finish(backend)
    evidence.append(asdict(result))
    t.check('natural void return', (result.outcome,result.value_state), ('returned','void'))
    t.reach('app_loop')
    other = t.breakpoint('board_led_toggle')
    try:
        result = finish(backend)
        evidence.append(asdict(result))
        t.check('foreign stop is interruption', result.outcome, 'interrupted')
        t.check('foreign breakpoint preserved', other.is_valid(), True)
        t.check('foreign breakpoint reported', other.number in result.breakpoints, True)
    finally:
        if other.is_valid(): other.delete()
    # Two additional points fill the six-slot profile alongside four fault guards.
    extras = []
    try:
        extras.append(t.breakpoint('board_adc_sample'))
        extras.append(t.breakpoint('board_delay_ms'))
        refused = False
        try:
            finish(backend)
        except FinishError as exc:
            refused = 'headroom' in str(exc)
        t.check('capacity refused before continue', refused, True)
    finally:
        for bp in extras:
            if bp.is_valid(): bp.delete()
    t.check('only original fault guards remain',
            [bp.number for bp in t.owned if bp.is_valid()], guards)
    t.report['e4_evidence'] = evidence
