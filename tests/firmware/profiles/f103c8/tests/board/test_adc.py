"""
RU: Проверки ADC: DMA, пересчёт измерений и управляемые отказы.
EN: ADC DMA acquisition, measurement conversion and controlled faults.
"""
from stm32_gdbtest import case


# Evaluate table rows in order and stop at the first failed read or check.
def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)

        # Compare the current row after both expressions have been evaluated.
        target.check(name, actual, expected)


# Verify ADC channels, sampling configuration, DMA and interrupt routing.
@case("HW_CI_ADC_INIT", labels=("adc", "dma", "init"), contracts=("ci_adc_macros",))
def adc_init(t):
    # TECH-001/002: independent expectations, device macros in adc_f103.c.
    t.reach("board_adc_sample")

    # Check register and application state against the expected values.
    _check_values(t, [
        ('ADC1 clock', '(RCC->APB2ENR & RCC_APB2ENR_ADC1EN) != 0', 1),
        ('DMA1 clock', '(RCC->AHBENR & RCC_AHBENR_DMA1EN) != 0', 1),
        ('ADC clock PCLK2/2 (4 MHz)', 'RCC->CFGR & RCC_CFGR_ADCPRE', 0),
        ('scan only, independent ADC', 'ADC1->CR1', 256),
        ('ADC enabled, internal sources, DMA, software trigger', 'ADC1->CR2', 10354945),
        ('sample CH16/17 at 239.5 cycles', 'ADC1->SMPR1', 16515072),
        ('two regular ranks', 'ADC1->SQR1', 1 << 20),
        ('CH16 then CH17', 'ADC1->SQR3', 16 | 17 << 5),
        ('normal DMA halfwords, TC/TE IRQ', 'DMA1_Channel1->CCR', 1418),
        ('ADC data address', 'DMA1_Channel1->CPAR', '&ADC1->DR'),
        ('SRAM buffer address', 'DMA1_Channel1->CMAR', '&board_adc_buffer[0]'),
        ('DMA NVIC enabled', '(NVIC->ISER[0] >> 11) & 1', 1),
        ('DMA vector', '(unsigned int)vectors[27] & ~1U', '(unsigned int)DMA1_Channel1_IRQHandler & ~1U'),
        ('no init error', 'board_adc_error', 0)
    ])


# Observe completed DMA transfers and validate the published ADC samples.
@case("HW_CI_ADC_DMA", labels=("adc", "dma", "runtime"), contracts=("ci_adc_macros",))
def adc_dma(t):
    # Follow successive DMA publications and compare raw and published samples.
    for sequence in (1, 2):
        t.reach("DMA1_Channel1_IRQHandler")

        # Check register and application state against the expected values.
        _check_values(t, [
            ('DMA exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 27),
            ('two transfers completed', 'DMA1_Channel1->CNDTR', 0),
            ('TC, no transfer error', 'DMA1->ISR & (DMA_ISR_TCIF1 | DMA_ISR_TEIF1)', 2)
        ])

        raw = [t.value(f"board_adc_buffer[{i}]") for i in range(2)]
        t.reach("board_delay_ms")

        # Check the publication counter before comparing measurement contents.
        t.check("published sequence", t.value("board_adc_sequences"), sequence)

        # Compare each published channel with its captured DMA value and reject saturation.
        for name, expected in zip(("board_temperature_raw", "board_reference_raw"), raw):
            # Verify the current sample against its expected value and validity bounds.
            t.check(name, t.value(name), expected)
            t.check(name + " not saturated", 0 < expected < 4095, True)

        # Check register and application state against the expected values.
        _check_values(t, [
            ('DMA stopped', 'DMA1_Channel1->CCR & DMA_CCR_EN', 0),
            ('DMA flags cleared', 'DMA1->ISR & 15', 0),
            ('no acquisition error', 'board_adc_error', 0)
        ])


# Check measurement provenance and plausible VDDA and die temperature.
@case("HW_CI_ADC_UNITS", labels=("adc", "units"), contracts=("ci_adc_units",))
def adc_units(t):
    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check measurement provenance and plausible physical ranges.
    t.check("typical provenance", t.value("board_adc_reading.quality"), 1)
    t.check("plausible VDDA", 2800 <= t.value("board_adc_reading.vdda_mv") <= 3600, True)
    t.check("plausible die temperature", -40000 <= t.value("board_adc_reading.temperature_mdeg_c") <= 125000, True)

    t.report["measurement"] = {name: t.value("board_adc_reading." + name)
                               for name in ("vdda_mv", "temperature_mdeg_c", "quality")}


# Inject conversion inputs and compare the published reading with fixed expectations.
def convert(t, values, expected):
    t.reach("adc_convert_f103")

    # Replace each conversion argument with the corresponding test input.
    for name, value in zip(("temperature", "reference"), values):
        t.set_value(name, value)

    t.reach("board_delay_ms")

    # Check the published fields against the expected values.
    t.fields("board_adc_reading", dict(zip(("vdda_mv", "temperature_mdeg_c", "quality"), expected)))


# Check conversion arithmetic against independent numerical reference vectors.
@case("HW_CI_ADC_VECTORS", labels=("adc", "arithmetic"), contracts=("ci_adc_units",))
def adc_vectors(t):
    # TECH-007: fixed analytic anchors, not expectations calculated by firmware.
    for inputs, expected in (
        ((1716, 1440), (3412, 25000, 1)),
        ((2145, 1800), (2730, 25000, 1)),
        ((1974, 1440), (3412, -25000, 1)),
        ((1329, 1440), (3412, 100000, 1))
    ):
        convert(t, inputs, expected)


# Reject invalid conversion inputs and verify subsequent measurement recovery.
@case("HW_CI_ADC_INVALID", timeout_s=60, labels=("adc", "negative", "arithmetic"), contracts=("ci_adc_units",))
def adc_invalid(t):
    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for index in range(2):
        # Cover zero, saturation and out-of-range values for this argument.
        for bad in (0, 4095, 65535):
            values = [1716, 1440]
            values[index] = bad
            convert(t, values, (0, 0, 0))

    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for reference in (1, 4000):
        convert(t, (1716, reference), (0, 0, 0))

    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check that valid acquisition resumes after the injected failures.
    t.check("normal acquisition recovers", t.value("board_adc_reading.quality"), 1)


# Verify that the ADC fault path publishes neither a sequence nor a valid reading.
def no_publication(t, error):
    t.reach("board_adc_fault")

    # Check the failure code and absence of a published measurement.
    t.check("error code", t.value("board_adc_error"), error)
    t.check("no sequence published", t.value("board_adc_sequences"), 0)
    t.check("no valid reading published", t.value("board_adc_reading.quality"), 0)


# Suppress completion notification and verify the ADC deadline and fault state.
@case("HW_CI_ADC_TIMEOUT", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_timeout(t):
    # TECH-006: IRQ masking removes notification, not the physical conversion.
    t.reach("board_adc_sample")
    start = t.value("board_ticks_ms")
    t.set_value("NVIC->ICER[0]", 1 << 11)
    no_publication(t, 4)

    # Check the elapsed deadline and DMA completion without notification.
    t.check("completion deadline", ((t.value("board_ticks_ms") - start) & 0xFFFFFFFF) >= 20, True)
    t.check("DMA completed without notification", t.value("DMA1_Channel1->CNDTR"), 0)


# Inject a busy acquisition state and verify that the next start is rejected.
@case("HW_CI_ADC_BUSY", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_busy(t):
    # TECH-006: enforce a DMA ownership guard, not a claim of F0 ADSTART semantics.
    t.reach("board_adc_sample")
    t.set_value("DMA1_Channel1->CNDTR", 2)
    t.set_value("DMA1_Channel1->CCR", t.value("DMA1_Channel1->CCR") | 1)

    # Verify DMA enabled before application start.
    t.check("DMA enabled before application start", t.value("DMA1_Channel1->CCR & DMA_CCR_EN"), 1)

    no_publication(t, 6)
    t.report["injection_scope"] = "DMA enable before sample; no claim of active ADC conversion"


# Disable the ADC and verify the application fault path.
@case("HW_CI_ADC_DISABLED", labels=("adc", "negative"), contracts=("ci_adc_macros",))
def adc_disabled(t):
    # TECH-006: real ADC disable, not a forced HAL status return.
    t.reach("board_adc_sample")
    t.set_value("ADC1->CR2", t.value("ADC1->CR2") & ~1)

    # Verify ADC powered off.
    t.check("ADC powered off", t.value("ADC1->CR2 & ADC_CR2_ADON"), 0)

    no_publication(t, 3)
