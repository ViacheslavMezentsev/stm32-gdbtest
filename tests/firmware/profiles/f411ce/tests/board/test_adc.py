"""
RU: Проверки ADC: DMA, пересчёт измерений и управляемые отказы.
EN: ADC DMA acquisition, measurement conversion and controlled faults.
"""
from stm32_gdbtest import case


# Evaluate table rows in order and stop at the first failed read or check.
def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.evaluate(expression, as_type=int)
        if isinstance(expected, str):
            # An expected cell may be a C expression, an address or an enum, so it is evaluated too.
            expected = target.evaluate(expected, as_type=int)

        # Compare the current row after both expressions have been evaluated.
        target.check(name, actual, expected)


# Verify ADC channels, sampling configuration, DMA and interrupt routing.
@case("HW_CI_ADC_INIT", labels=("adc", "dma", "init"), contracts=("ci_adc_macros",))
def adc_init(t):
    # TECH-001/002: independent expectations, device macros in adc_f411.c.
    t.reach("board_adc_sample")

    # Check register and application state against the expected values.
    _check_values(t, [
        ('ADC1 clock', '(RCC->APB2ENR & RCC_APB2ENR_ADC1EN) != 0', 1),
        ('DMA2 clock', '(RCC->AHB1ENR & RCC_AHB1ENR_DMA2EN) != 0', 1),
        ('ADC clock PCLK2/2 (8 MHz)', 'ADC->CCR & ADC_CCR_ADCPRE', 0),
        ('scan only, independent ADC', 'ADC1->CR1', 256),
        ('ADC enabled, internal sources, DMA, software trigger', 'ADC1->CR2', 769),
        ('sample CH18/17 at 480 cycles', 'ADC1->SMPR1', 132120576),
        ('two regular ranks', 'ADC1->SQR1', 1 << 20),
        ('CH18 then CH17', 'ADC1->SQR3', 18 | 17 << 5),
        ('normal DMA halfwords, TC/TE/DME IRQ', 'DMA2_Stream0->CR', 11286),
        ('ADC data address', 'DMA2_Stream0->PAR', '&ADC1->DR'),
        ('SRAM buffer address', 'DMA2_Stream0->M0AR', '&board_adc_buffer[0]'),
        ('DMA NVIC enabled', '(NVIC->ISER[1] >> 24) & 1', 1),
        ('DMA vector', '(unsigned int)vectors[72] & ~1U', '(unsigned int)DMA2_Stream0_IRQHandler & ~1U'),
        ('internal sources without VBAT', 'ADC->CCR', 1 << 23),
        ('direct DMA mode', 'DMA2_Stream0->FCR & 0x84', 0),
        ('no init error', 'board_adc_error', 0)
    ])


# Observe completed DMA transfers and validate the published ADC samples.
@case("HW_CI_ADC_DMA", labels=("adc", "dma", "runtime"), contracts=("ci_adc_macros",))
def adc_dma(t):
    # Follow successive DMA publications and compare raw and published samples.
    for sequence in (1, 2):
        t.reach("DMA2_Stream0_IRQHandler")

        # Check register and application state against the expected values.
        _check_values(t, [
            ('DMA exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 72),
            ('two transfers completed', 'DMA2_Stream0->NDTR', 0),
            (
                'TC, no transfer error',
                'DMA2->LISR & (DMA_LISR_TCIF0 | DMA_LISR_TEIF0 | DMA_LISR_DMEIF0 | DMA_LISR_FEIF0)',
                32
            )
        ])

        raw = [t.read(f"board_adc_buffer[{i}]") for i in range(2)]
        t.reach("board_delay_ms")

        # Check the publication counter before comparing measurement contents.
        t.check("published sequence", t.read("board_adc_sequences"), sequence)

        # Compare each published channel with its captured DMA value and reject saturation.
        for name, expected in zip(("board_temperature_raw", "board_reference_raw"), raw):
            # Verify the current sample against its expected value and validity bounds.
            t.check(name, t.read(name), expected)
            t.check(name + " not saturated", 0 < expected < 4095, True)

        # Check register and application state against the expected values.
        _check_values(t, [
            ('DMA stopped', 'DMA2_Stream0->CR & DMA_SxCR_EN', 0),
            ('DMA flags cleared', 'DMA2->LISR & 0x3D', 0),
            ('no acquisition error', 'board_adc_error', 0)
        ])


# Check measurement provenance and plausible VDDA and die temperature.
@case("HW_CI_ADC_UNITS", labels=("adc", "units"), contracts=("ci_adc_units",))
def adc_units(t):
    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check measurement provenance and plausible physical ranges.
    t.check("factory provenance", t.read("board_adc_reading.quality"), 2)
    t.check("plausible VDDA", 2800 <= t.read("board_adc_reading.vdda_mv") <= 3600, True)
    t.check("plausible die temperature", -40000 <= t.read("board_adc_reading.temperature_mdeg_c") <= 125000, True)

    t.report["measurement"] = {name: t.read("board_adc_reading." + name)
                               for name in ("vdda_mv", "temperature_mdeg_c", "quality")}


# Inject conversion inputs and compare the published reading with fixed expectations.
def convert(t, values, expected):
    t.reach("adc_convert_f4_factory")

    # Replace each conversion argument with the corresponding test input.
    for name, value in zip(
        ("temperature", "reference", "reference_cal", "temperature_cal1", "temperature_cal2"),
        values
    ):
        t.write(name, value)

    t.reach("board_delay_ms")

    # Check the published fields against the expected values.
    t.fields("board_adc_reading", dict(zip(("vdda_mv", "temperature_mdeg_c", "quality"), expected)))


# Check conversion arithmetic against independent numerical reference vectors.
@case("HW_CI_ADC_VECTORS", labels=("adc", "arithmetic"), contracts=("ci_adc_units",))
def adc_vectors(t):
    # TECH-007: fixed analytic anchors, not expectations calculated by firmware.
    for inputs, expected in (
        ((1000, 1500, 1500, 1000, 2000), (3300, 30000, 2)),
        ((2000, 1500, 1500, 1000, 2000), (3300, 110000, 2)),
        ((1500, 1500, 1500, 1000, 2000), (3300, 70000, 2)),
        ((500, 1500, 1500, 1000, 2000), (3300, -10000, 2)),
        ((1250, 1875, 1500, 1000, 2000), (2640, 30000, 2))
    ):
        convert(t, inputs, expected)


# Reject invalid conversion inputs and verify subsequent measurement recovery.
@case("HW_CI_ADC_INVALID", timeout_s=60, labels=("adc", "negative", "arithmetic"), contracts=("ci_adc_units",))
def adc_invalid(t):
    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for index in range(5):
        # Cover zero, saturation and out-of-range values for this argument.
        for bad in (0, 4095, 65535):
            values = [1000, 1500, 1500, 1000, 2000]
            values[index] = bad
            convert(t, values, (0, 0, 0))

    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for values in ((1000, 1500, 1500, 1000, 1000),
                   (1000, 1500, 1500, 2000, 1000),
                   (1000, 1, 1500, 1000, 2000),
                   (1000, 4000, 1500, 1000, 2000)):
        convert(t, values, (0, 0, 0))

    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check that valid acquisition resumes after the injected failures.
    t.check("normal acquisition recovers", t.read("board_adc_reading.quality"), 2)


# Verify that the ADC fault path publishes neither a sequence nor a valid reading.
def no_publication(t, error):
    t.reach("board_adc_fault")

    # Check the failure code and absence of a published measurement.
    t.check("error code", t.read("board_adc_error"), error)
    t.check("no sequence published", t.read("board_adc_sequences"), 0)
    t.check("no valid reading published", t.read("board_adc_reading.quality"), 0)


# Suppress completion notification and verify the ADC deadline and fault state.
@case("HW_CI_ADC_TIMEOUT", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_timeout(t):
    # TECH-006: IRQ masking removes notification, not the physical conversion.
    t.reach("board_adc_sample")
    start = t.read("board_ticks_ms")
    t.write("NVIC->ICER[1]", 1 << 24)
    no_publication(t, 4)

    # Check the elapsed deadline and DMA completion without notification.
    t.check("completion deadline", ((t.read("board_ticks_ms") - start) & 0xFFFFFFFF) >= 20, True)
    t.check("DMA completed without notification", t.read("DMA2_Stream0->NDTR"), 0)


# Inject a busy acquisition state and verify that the next start is rejected.
@case("HW_CI_ADC_BUSY", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_busy(t):
    # TECH-006: enforce a DMA ownership guard, not a claim of F0 ADSTART semantics.
    t.reach("board_adc_sample")
    t.write("DMA2_Stream0->NDTR", 2)
    t.write("DMA2_Stream0->CR", t.read("DMA2_Stream0->CR") | 1)

    # Verify DMA enabled before application start.
    t.check("DMA enabled before application start", t.read("DMA2_Stream0->CR & DMA_SxCR_EN"), 1)

    no_publication(t, 6)
    t.report["injection_scope"] = "DMA enable before sample; no claim of active ADC conversion"


# Disable the ADC and verify the application fault path.
@case("HW_CI_ADC_DISABLED", labels=("adc", "negative"), contracts=("ci_adc_macros",))
def adc_disabled(t):
    # TECH-006: real ADC disable, not a forced HAL status return.
    t.reach("board_adc_sample")
    t.write("ADC1->CR2", t.read("ADC1->CR2") & ~1)

    # Verify ADC powered off.
    t.check("ADC powered off", t.read("ADC1->CR2 & ADC_CR2_ADON"), 0)

    no_publication(t, 3)
