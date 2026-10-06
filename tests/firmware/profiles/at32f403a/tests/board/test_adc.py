"""
RU: Проверки ADC AT32F403A: DMA, пересчёт измерений и управляемые отказы.
EN: AT32F403A ADC DMA acquisition, measurement conversion and controlled faults.
"""
from stm32_gdbtest import case, within


# Full scale of the 12-bit ADC: 0 and 4095 are saturated readings.
ADC_FULL_SCALE = 4095
# One DMA sequence carries the temperature and VINTRV samples.
SAMPLES_PER_SEQUENCE = 2

# Plausibility windows of a reading; not a calibration or accuracy claim.
PLAUSIBLE_VDDA_MV = within(2800, 3600)
PLAUSIBLE_DIE_MDEG_C = within(-40_000, 125_000)

# ADC channels of the internal sensors (RM 19.4.1): temperature sensor IN16 and VINTRV IN17.
TEMPERATURE_CHANNEL = 16
VINTRV_CHANNEL = 17
# Register values the firmware must configure, from the RM bit positions (independent of the firmware):
# ADC_CTRL1 = SQEN only (RM 19.6.2); ADC_CTRL2 = ADCEN | OCDMAEN | OCTESEL 0111 (OCSWTRG) | OCTEN | ITSRVEN (RM 19.6.3);
# DMA channel control = FDTIEN | DTERRIEN | MINCM | PWIDTH 16 bit | MWIDTH 16 bit.
ADC_CTRL1_SCAN = 1 << 8
ADC_CTRL2_RUNNING = (1 << 0) | (1 << 8) | (7 << 17) | (1 << 20) | (1 << 23)
DMA_CTRL_IDLE = (1 << 1) | (1 << 3) | (1 << 7) | (1 << 8) | (1 << 10)
# Sample time code 111 (239.5 cycles) for IN16 and IN17, two ordinary ranks.
SAMPLE_TIME_MAX = 7
ORDINARY_RANKS = 2
# Provenance of a published reading (adc_units.c): 0 invalid, 4 vendor example constants.
QUALITY_INVALID = 0
QUALITY_VENDOR = 4
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
    # TECH-001/002: independent expectations, device macros in adc_at32f403a.c.
    t.reach("board_adc_sample")

    # Check register and application state against the expected values.
    t.check([
        ('ADC1 clock', 'CRM->apb2en_bit.adc1en', 1),
        ('DMA1 clock', 'CRM->ahben_bit.dma1en', 1),
        ('ADC clock PCLK2/2 (4 MHz)', 'CRM->cfg_bit.adcdiv_l | CRM->cfg_bit.adcdiv_h', 0),
        ('scan only, independent ADC', 'ADC1->ctrl1', ADC_CTRL1_SCAN),
        ('ADC enabled, internal sources, DMA, software trigger', 'ADC1->ctrl2', ADC_CTRL2_RUNNING),
        ('sample IN16 at 239.5 cycles', 'ADC1->spt1_bit.cspt16', SAMPLE_TIME_MAX),
        ('sample IN17 at 239.5 cycles', 'ADC1->spt1_bit.cspt17', SAMPLE_TIME_MAX),
        ('two ordinary ranks', 'ADC1->osq1_bit.oclen', ORDINARY_RANKS - 1),
        ('IN16 first', 'ADC1->osq3_bit.osn1', TEMPERATURE_CHANNEL),
        ('IN17 second', 'ADC1->osq3_bit.osn2', VINTRV_CHANNEL),
        ('normal DMA halfwords, FDT/DTERR IRQ', 'DMA1_CHANNEL1->ctrl', DMA_CTRL_IDLE),
        ('ADC data address', 'DMA1_CHANNEL1->paddr', '&ADC1->odt'),
        ('SRAM buffer address', 'DMA1_CHANNEL1->maddr', '&board_adc_buffer[0]'),
        ('DMA NVIC enabled', 'NVIC->ISER[DMA1_Channel1_IRQn >> 5] & (1UL << (DMA1_Channel1_IRQn & 31))'),
        ('DMA vector', '(unsigned int)vectors[DMA1_Channel1_IRQn + 16] & ~1U',
         '(unsigned int)DMA1_Channel1_IRQHandler & ~1U'),
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
            ('two transfers completed', 'DMA1_CHANNEL1->dtcnt', 0),
            ('full transfer done', 'DMA1->sts_bit.fdtf1', 1),
            ('no transfer error', 'DMA1->sts_bit.dterrf1', 0)
        ])

        raw = [t.read(f"board_adc_buffer[{i}]") for i in range(SAMPLES_PER_SEQUENCE)]
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
            ('DMA stopped', 'DMA1_CHANNEL1->ctrl_bit.chen', 0),
            ('DMA flags cleared', 'DMA1->sts & 15', 0),
            ('no acquisition error', 'board_adc_error', 0)
        ])


# Check measurement provenance and plausible VDDA and die temperature.
@case("HW_CI_ADC_UNITS", labels=("adc", "units"), contracts=("ci_adc_units",))
def adc_units(t):
    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check measurement provenance and plausible physical ranges.
    t.check([
        ("vendor provenance", "board_adc_reading.quality", QUALITY_VENDOR),
        ("plausible VDDA", "board_adc_reading.vdda_mv", PLAUSIBLE_VDDA_MV),
        ("plausible die temperature", "board_adc_reading.temperature_mdeg_c", PLAUSIBLE_DIE_MDEG_C)
    ])

    t.report["measurement"] = {name: t.read("board_adc_reading." + name)
                               for name in ("vdda_mv", "temperature_mdeg_c", "quality")}


# Inject conversion inputs and compare the published reading with fixed expectations.
def convert(t, values, expected):
    t.reach("adc_convert_at32f403a")

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
    # TECH-007: anchors of T = 25 + (Vsense - 1.26 V) / 4.23 mV, Vsense = 1.2 V * t / r, VDDA = 1.2 V * 4095 / r,
    # integer truncation as in C; not values calculated by the firmware.
    for inputs, expected in (
        ((1512, 1440), (3412, 25000, QUALITY_VENDOR)),
        ((1890, 1800), (2730, 25000, QUALITY_VENDOR)),
        ((1258, 1440), (3412, -25039, QUALITY_VENDOR)),
        ((1893, 1440), (3412, 100059, QUALITY_VENDOR))
    ):
        convert(t, inputs, expected)


# Reject invalid conversion inputs and verify subsequent measurement recovery.
@case("HW_CI_ADC_INVALID", timeout_s=60, labels=("adc", "negative", "arithmetic"), contracts=("ci_adc_units",))
def adc_invalid(t):
    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for index in range(2):
        # Cover zero, saturation and out-of-range values for this argument.
        for bad in (0, 4095, 65535):
            values = [1512, 1440]
            values[index] = bad
            convert(t, values, (0, 0, 0))

    # Exercise implausible VDDA values, then verify that normal acquisition recovers.
    for reference in (1, 4000):
        convert(t, (1512, reference), (0, 0, 0))

    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check that valid acquisition resumes after the injected failures.
    t.check("normal acquisition recovers", t.read("board_adc_reading.quality"), QUALITY_VENDOR)


# Verify that the ADC fault path publishes neither a sequence nor a valid reading.
def no_publication(t, error):
    t.reach("board_adc_fault")

    # Check the failure code and absence of a published measurement.
    t.check([
        ("error code", "board_adc_error", error),
        ("no sequence published", "board_adc_sequences", 0),
        ("no valid reading published", "board_adc_reading.quality", QUALITY_INVALID)
    ])


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
    t.check("DMA completed without notification", t.read("DMA1_CHANNEL1->dtcnt"), 0)


# Inject a busy acquisition state and verify that the next start is rejected.
@case("HW_CI_ADC_BUSY", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_busy(t):
    # TECH-006: enforce a DMA ownership guard, not a claim of an ADC busy bit.
    t.reach("board_adc_sample")

    # Arm a transfer of one sequence and enable DMA before the application starts its own.
    t.write([
        ("DMA1_CHANNEL1->dtcnt", SAMPLES_PER_SEQUENCE),
        ("DMA1_CHANNEL1->ctrl", "DMA1_CHANNEL1->ctrl | 1")
    ])

    # Verify DMA enabled before application start.
    t.check("DMA enabled before application start", t.read("DMA1_CHANNEL1->ctrl_bit.chen"), 1)

    no_publication(t, ADC_ERROR_BUSY)
    t.report["injection_scope"] = "DMA enable before sample; no claim of active ADC conversion"


# Disable the ADC and verify the application fault path.
@case("HW_CI_ADC_DISABLED", labels=("adc", "negative"), contracts=("ci_adc_macros",))
def adc_disabled(t):
    # TECH-006: real ADC disable, not a forced driver status return.
    t.reach("board_adc_sample")
    t.write("ADC1->ctrl2", "ADC1->ctrl2 & ~1U")

    # Verify ADC powered off.
    t.check("ADC powered off", t.read("ADC1->ctrl2_bit.adcen"), 0)

    no_publication(t, ADC_ERROR_INIT)
