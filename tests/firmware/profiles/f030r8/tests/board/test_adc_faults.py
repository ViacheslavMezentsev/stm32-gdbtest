"""
RU: Проверка отказа запуска ADC при занятом преобразователе.
EN: ADC start rejection under a controlled busy condition.
"""
from stm32_gdbtest import case

# board_adc_error code of a rejected start (adc_f030.c).
ADC_ERROR_BUSY = 6
# Quality of an absent reading (adc_units.c).
QUALITY_INVALID = 0


# Inject a busy acquisition state and verify that the next start is rejected.
@case("HW_CI_ADC_BUSY", labels=("adc", "negative"), contracts=("ci_adc_macros",))
def adc_busy(t):
    # TECH-006: docs/ru/TESTING_TECHNIQUES.md#tech-006 (EN: docs/en/TESTING_TECHNIQUES.md#tech-006).
    t.reach("board_adc_sample")

    # Verify initial ADC idle.
    t.check("initial ADC idle", t.read("ADC1->CR & ADC_CR_ADSTART"), 0)

    # Start continuous conversions while the core is halted: ADSTART stays asserted.
    t.write("ADC1->CFGR1", t.read("ADC1->CFGR1") | t.evaluate("ADC_CFGR1_CONT"))
    t.write("ADC1->CR", t.read("ADC1->CR") | t.evaluate("ADC_CR_ADSTART"))

    # Verify conversion is active.
    t.check("conversion is active", t.read("ADC1->CR & ADC_CR_ADSTART"))

    t.reach("board_adc_fault")

    # Check register and application state against the expected values.
    t.check([
        ('busy start rejected', 'board_adc_error', ADC_ERROR_BUSY),
        ('no sequence published', 'board_adc_sequences', 0),
        ('no valid measurement published', 'board_adc_reading.quality', QUALITY_INVALID)
    ])

    t.report["injection_scope"] = "ADC continuous conversion before application start; teardown reset_run"
