"""
RU: Накопление измерений VDDA и температуры MCU, вычисление среднего и СКО.
EN: Collect MCU VDDA and temperature samples, then calculate mean and standard deviation.
"""
from statistics import mean, stdev
from stm32_gdbtest import case


# Collect consecutive ADC publications and summarize them using runtime records.
@case("HW_CI_ADC_SERIES", timeout_s=60, labels=("adc", "units", "series"), contracts=("ci_adc_units",))
def adc_series(target):
    # Read measurement parameters from the session's API configuration.
    settings = target.config["api"]["user"]["measurement"]
    count, quality = settings["count"], settings["expected_quality"]

    # Reject unsupported parameters before navigating or reading the MCU.
    target.check("series count is integer 2..20", type(count) is int and 2 <= count <= 20, True)
    target.check("known quality", type(quality) is int and quality in (1, 2, 3), True)

    # Each scenario invocation must start with an empty runtime journal.
    target.check("fresh scenario journal", target.records(), [])

    previous = None

    # Advance through complete ADC publications and retain each sample.
    # Sequence checks prevent repeated or skipped publications within the series.
    for index in range(count):
        target.reach("board_adc_sample")
        target.reach("board_delay_ms")
        sequence = target.value("board_adc_sequences")

        # Compare publication counters with unsigned 32-bit wraparound.
        if previous is not None:
            target.check("fresh contiguous publication", (sequence - previous) & 0xFFFFFFFF, 1)

        # Snapshot the published values while the MCU is stopped.
        sample = {
            name: target.value("board_adc_reading." + name)
            for name in ("vdda_mv", "temperature_mdeg_c", "quality")
        }

        # Retain the sample before validation so rejected readings remain in the runtime journal.
        target.record("adc.sample", dict(sample, sequence=sequence, index=index))

        # Check measurement provenance and plausible physical ranges.
        target.check("expected provenance", sample["quality"], quality)
        target.check("plausible VDDA", 2800 <= sample["vdda_mv"] <= 3600, True)
        target.check("plausible temperature", -40000 <= sample["temperature_mdeg_c"] <= 125000, True)

        previous = sequence

    # Select measurement records and verify that the series is complete.
    samples = [r["data"] for r in target.records("adc.sample")]
    target.check("complete series", len(samples), count)

    # Calculate statistics without reading the MCU again; convert temperature to degrees Celsius.
    voltage = [s["vdda_mv"] for s in samples]
    temperature = [s["temperature_mdeg_c"] / 1000 for s in samples]

    # Store a separate summary. stdev() uses the sample denominator N - 1.
    target.record(
        "adc.summary",
        dict(
            count=count, ddof=1,
            vdda_mv=dict(mean=mean(voltage), stdev=stdev(voltage)),
            temperature_c=dict(mean=mean(temperature), stdev=stdev(temperature))
        )
    )

    # Confirm that the journal contains all samples and one summary.
    target.check("samples and summary retained", len(target.records()), count + 1)
