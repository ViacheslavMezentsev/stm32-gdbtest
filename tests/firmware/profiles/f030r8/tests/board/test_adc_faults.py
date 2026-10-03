"""Controlled ADC state injection; no firmware hooks or HAL return override."""
from stm32_gdbtest import case




def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)
        target.check(name, actual, expected)


@case("HW_CI_ADC_BUSY", labels=("adc", "negative"), contracts=("ci_adc_macros",))
def adc_busy(target):
    # TECH-006: docs/ru/TESTING_TECHNIQUES.md#tech-006 (EN: docs/en/TESTING_TECHNIQUES.md#tech-006).
    target.reach("board_adc_sample")
    target.check("initial ADC idle", target.value("ADC1->CR & ADC_CR_ADSTART"), 0)
    # Start continuous conversions while the core is halted: ADSTART stays asserted.
    target.set_value("ADC1->CFGR1", target.value("ADC1->CFGR1") | (1 << 13))
    target.set_value("ADC1->CR", target.value("ADC1->CR") | (1 << 2))
    target.check("conversion is active", target.value("ADC1->CR & ADC_CR_ADSTART"), 1 << 2)
    target.reach("board_adc_fault")
    _check_values(target, [
        ('busy start rejected', 'board_adc_error', 6),
        ('no sequence published', 'board_adc_sequences', 0),
        ('no valid measurement published', 'board_adc_reading.quality', 0),
    ])
    target.report["injection_scope"] = "ADC continuous conversion before application start; teardown reset_run"
