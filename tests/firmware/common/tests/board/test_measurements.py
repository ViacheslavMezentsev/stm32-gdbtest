"""
RU: Накопление измерений VDDA и температуры MCU, вычисление среднего и СКО.
EN: Collect MCU VDDA and temperature samples, then calculate mean and standard deviation.
"""
from statistics import mean, stdev
from stm32_gdbtest import case, one_of, within


# Accepted series lengths and provenance codes (adc_units.c: 1 typical, 2 two-point, 3 one-point,
# 4 vendor example constants).
SERIES_LENGTH = within(2, 20)
KNOWN_QUALITY = one_of(1, 2, 3, 4)
# Plausibility windows of a reading; not a calibration or accuracy claim.
PLAUSIBLE_VDDA_MV = within(2800, 3600)
PLAUSIBLE_DIE_MDEG_C = within(-40_000, 125_000)
# Publication counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF


# Collect consecutive ADC publications and summarize them using runtime records.
@case("HW_CI_ADC_SERIES", timeout_s=60, labels=("adc", "units", "series"), contracts=("ci_adc_units",))
def adc_series(t):
    # Read measurement parameters from the user section of the run profile (api.toml [user]).
    settings = t.profile.user["measurement"]
    count, quality = settings["count"], settings["expected_quality"]

    # Reject unsupported parameters before navigating or reading the MCU.
    t.check("series count is an integer", type(count) is int)
    t.check("series count 2..20", count, SERIES_LENGTH)
    t.check("known quality", quality, KNOWN_QUALITY)

    # Each scenario invocation must start with an empty runtime journal.
    t.check("fresh scenario journal", t.records(), [])

    previous = None

    # Advance through complete ADC publications and retain each sample.
    # Sequence checks prevent repeated or skipped publications within the series.
    for index in range(count):
        t.reach("board_adc_sample")
        t.reach("board_delay_ms")
        sequence = t.read("board_adc_sequences")

        # Compare publication counters with unsigned 32-bit wraparound.
        if previous is not None:
            t.check("fresh contiguous publication", (sequence - previous) & U32_MASK, 1)

        # Snapshot the published values while the MCU is stopped.
        sample = {name: t.read("board_adc_reading." + name) for name in ("vdda_mv", "temperature_mdeg_c", "quality")}

        # Retain the sample before validation so rejected readings remain in the runtime journal.
        t.record("adc.sample", dict(sample, sequence=sequence, index=index))

        # Check measurement provenance and plausible physical ranges.
        t.check("expected provenance", sample["quality"], quality)
        t.check("plausible VDDA", sample["vdda_mv"], PLAUSIBLE_VDDA_MV)
        t.check("plausible temperature", sample["temperature_mdeg_c"], PLAUSIBLE_DIE_MDEG_C)

        previous = sequence

    # Select measurement records and verify that the series is complete.
    samples = [r["data"] for r in t.records("adc.sample")]
    t.check("complete series", len(samples), count)

    # Calculate statistics without reading the MCU again; convert temperature to degrees Celsius.
    voltage = [s["vdda_mv"] for s in samples]
    temperature = [s["temperature_mdeg_c"] / 1000 for s in samples]

    # Store a separate summary. stdev() uses the sample denominator N - 1.
    t.record(
        "adc.summary",
        dict(
            count=count, ddof=1,
            vdda_mv=dict(mean=mean(voltage), stdev=stdev(voltage)),
            temperature_c=dict(mean=mean(temperature), stdev=stdev(temperature))
        )
    )

    # Confirm that the journal contains all samples and one summary.
    t.check("samples and summary retained", len(t.records()), count + 1)
