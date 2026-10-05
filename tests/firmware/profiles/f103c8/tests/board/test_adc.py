"""
RU: Проверки ADC: DMA, пересчёт измерений и управляемые отказы.
EN: ADC DMA acquisition, measurement conversion and controlled faults.
"""
from stm32_gdbtest import case, within

# Full scale of the 12-bit ADC: 0 and 4095 are saturated readings.
ADC_FULL_SCALE = 4095
# One DMA sequence carries the temperature and VREFINT samples.
SAMPLES_PER_SEQUENCE = 2

# Plausibility windows of a reading; not a calibration or accuracy claim.
PLAUSIBLE_VDDA_MV = within(2800, 3600)
PLAUSIBLE_DIE_MDEG_C = within(-40_000, 125_000)

# ADC channels of the internal sensors (RM, independent of the firmware): temperature
# sensor and VREFINT.
TEMPERATURE_CHANNEL = 16
VREFINT_CHANNEL = 17
# Provenance of a published reading (adc_units.c): 0 invalid, 1 typical datasheet values,
# 2 factory two-point calibration, 3 factory one-point calibration.
QUALITY_INVALID = 0
QUALITY_TYPICAL = 1
# board_adc_error codes of the fixture firmware (adc_*.c).
ADC_ERROR_NONE = 0
ADC_ERROR_INIT = 3
ADC_ERROR_DEADLINE = 4
ADC_ERROR_BUSY = 6

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF


# Verify ADC channels, sampling configuration, DMA and interrupt routing.
@case("HW_CI_ADC_INIT", labels=("adc", "dma", "init"), contracts=("ci_adc_macros",))
def adc_init(t):
    # TECH-001/002: independent expectations, device macros in adc_f103.c.
    t.reach("board_adc_sample")

    # Check register and application state against the expected values.
    t.check([
        ('ADC1 clock', 'RCC->APB2ENR & RCC_APB2ENR_ADC1EN'),
        ('DMA1 clock', 'RCC->AHBENR & RCC_AHBENR_DMA1EN'),
        ('ADC clock PCLK2/2 (4 MHz)', 'RCC->CFGR & RCC_CFGR_ADCPRE', 0),
        ('scan only, independent ADC', 'ADC1->CR1', 'ADC_CR1_SCAN'),
        ('ADC enabled, internal sources, DMA, software trigger', 'ADC1->CR2',
         'ADC_CR2_ADON | ADC_CR2_TSVREFE | ADC_CR2_EXTSEL | ADC_CR2_EXTTRIG | ADC_CR2_DMA'),
        ('sample CH16/17 at 239.5 cycles', 'ADC1->SMPR1', 'ADC_SMPR1_SMP16 | ADC_SMPR1_SMP17'),
        ('two regular ranks', 'ADC1->SQR1', 'ADC_SQR1_L_0'),
        ('CH16 then CH17', 'ADC1->SQR3', TEMPERATURE_CHANNEL | VREFINT_CHANNEL << 5),
        ('normal DMA halfwords, TC/TE IRQ', 'DMA1_Channel1->CCR',
         'DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE'),
        ('ADC data address', 'DMA1_Channel1->CPAR', '&ADC1->DR'),
        ('SRAM buffer address', 'DMA1_Channel1->CMAR', '&board_adc_buffer[0]'),
        ('DMA NVIC enabled', 'NVIC->ISER[DMA1_Channel1_IRQn >> 5] & (1UL << (DMA1_Channel1_IRQn & 31))'),
        ('DMA vector', '(unsigned int)vectors[DMA1_Channel1_IRQn + 16] & ~1U', '(unsigned int)DMA1_Channel1_IRQHandler & ~1U'),
        ('no init error', 'board_adc_error', ADC_ERROR_NONE)
    ])


# Observe completed DMA transfers and validate the published ADC samples.
@case("HW_CI_ADC_DMA", labels=("adc", "dma", "runtime"), contracts=("ci_adc_macros",))
def adc_dma(t):
    # Follow successive DMA publications and compare raw and published samples.
    for sequence in (1, 2):
        t.reach("DMA1_Channel1_IRQHandler")

        # Check register and application state against the expected values.
        t.check([
            ('DMA exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 'DMA1_Channel1_IRQn + 16'),
            ('two transfers completed', 'DMA1_Channel1->CNDTR', 0),
            ('TC, no transfer error', 'DMA1->ISR & (DMA_ISR_TCIF1 | DMA_ISR_TEIF1)', 2)
        ])

        raw = [t.read(f"board_adc_buffer[{i}]") for i in range(2)]
        t.reach("board_delay_ms")

        # Check the publication counter before comparing measurement contents.
        t.check("published sequence", t.read("board_adc_sequences"), sequence)

        # Compare each published channel with its captured DMA value and reject saturation.
        for name, expected in zip(("board_temperature_raw", "board_reference_raw"), raw):
            # Verify the current sample against its expected value and validity bounds.
            t.check(name, t.read(name), expected)
            t.check(name + " not saturated", 0 < expected < ADC_FULL_SCALE)

        # Check register and application state against the expected values.
        t.check([
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
    t.check("typical provenance", t.read("board_adc_reading.quality"), QUALITY_TYPICAL)
    t.check("plausible VDDA", t.read("board_adc_reading.vdda_mv"), PLAUSIBLE_VDDA_MV)
    t.check("plausible die temperature", t.read("board_adc_reading.temperature_mdeg_c"),
            PLAUSIBLE_DIE_MDEG_C)

    t.report["measurement"] = {name: t.read("board_adc_reading." + name)
                               for name in ("vdda_mv", "temperature_mdeg_c", "quality")}


# Inject conversion inputs and compare the published reading with fixed expectations.
def convert(t, values, expected):
    t.reach("adc_convert_f103")

    # Replace each conversion argument with the corresponding test input.
    for name, value in zip(("temperature", "reference"), values):
        t.write(name, value)

    t.reach("board_delay_ms")

    # Check the published fields against the expected values.
    t.check([(f"board_adc_reading.{field}", f"board_adc_reading.{field}", value)
             for field, value in zip(("vdda_mv", "temperature_mdeg_c", "quality"), expected)])


# Check conversion arithmetic against independent numerical reference vectors.
@case("HW_CI_ADC_VECTORS", labels=("adc", "arithmetic"), contracts=("ci_adc_units",))
def adc_vectors(t):
    # TECH-007: fixed analytic anchors, not expectations calculated by firmware.
    for inputs, expected in (
        ((1716, 1440), (3412, 25000, QUALITY_TYPICAL)),
        ((2145, 1800), (2730, 25000, QUALITY_TYPICAL)),
        ((1974, 1440), (3412, -25000, 1)),
        ((1329, 1440), (3412, 100000, QUALITY_TYPICAL))
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
    t.check("normal acquisition recovers", t.read("board_adc_reading.quality"), QUALITY_TYPICAL)


# Verify that the ADC fault path publishes neither a sequence nor a valid reading.
def no_publication(t, error):
    t.reach("board_adc_fault")

    # Check the failure code and absence of a published measurement.
    t.check("error code", t.read("board_adc_error"), error)
    t.check("no sequence published", t.read("board_adc_sequences"), 0)
    t.check("no valid reading published", t.read("board_adc_reading.quality"), QUALITY_INVALID)


# Suppress completion notification and verify the ADC deadline and fault state.
@case("HW_CI_ADC_TIMEOUT", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_timeout(t):
    # TECH-006: IRQ masking removes notification, not the physical conversion.
    t.reach("board_adc_sample")
    start = t.read("board_ticks_ms")
    irq = t.evaluate("DMA1_Channel1_IRQn")
    t.write(f"NVIC->ICER[{irq >> 5}]", 1 << (irq & 31))
    no_publication(t, ADC_ERROR_DEADLINE)

    # Check the elapsed deadline and DMA completion without notification.
    t.check("completion deadline", ((t.read("board_ticks_ms") - start) & U32_MASK) >= 20)
    t.check("DMA completed without notification", t.read("DMA1_Channel1->CNDTR"), 0)


# Inject a busy acquisition state and verify that the next start is rejected.
@case("HW_CI_ADC_BUSY", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_busy(t):
    # TECH-006: enforce a DMA ownership guard, not a claim of F0 ADSTART semantics.
    t.reach("board_adc_sample")
    t.write([
        ("DMA1_Channel1->CNDTR", SAMPLES_PER_SEQUENCE),
        ("DMA1_Channel1->CCR", "DMA1_Channel1->CCR | DMA_CCR_EN"),
    ])

    # Verify DMA enabled before application start.
    t.check("DMA enabled before application start", t.read("DMA1_Channel1->CCR & DMA_CCR_EN"))

    no_publication(t, ADC_ERROR_BUSY)
    t.report["injection_scope"] = "DMA enable before sample; no claim of active ADC conversion"


# Disable the ADC and verify the application fault path.
@case("HW_CI_ADC_DISABLED", labels=("adc", "negative"), contracts=("ci_adc_macros",))
def adc_disabled(t):
    # TECH-006: real ADC disable, not a forced HAL status return.
    t.reach("board_adc_sample")
    t.write("ADC1->CR2", "ADC1->CR2 & ~ADC_CR2_ADON")

    # Verify ADC powered off.
    t.check("ADC powered off", t.read("ADC1->CR2 & ADC_CR2_ADON"), 0)

    no_publication(t, ADC_ERROR_INIT)
