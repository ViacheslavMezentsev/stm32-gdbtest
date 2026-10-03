"""TECH-011: independent published samples and Python statistics on runtime records."""
from statistics import mean, stdev
from stm32_gdbtest import case


@case("HW_CI_ADC_SERIES", timeout_s=60, labels=("adc", "units", "series"), contracts=("ci_adc_units",))
def adc_series(target):
    settings = target.config["api"]["user"]["measurement"]
    count, quality = settings["count"], settings["expected_quality"]
    target.check("series count is integer 2..20", type(count) is int and 2 <= count <= 20, True)
    target.check("known quality", type(quality) is int and quality in (1, 2, 3), True)
    target.check("fresh scenario journal", target.records(), [])
    previous = None
    for index in range(count):
        target.reach("board_adc_sample")
        target.reach("board_delay_ms")
        sequence = target.value("board_adc_sequences")
        if previous is not None:
            target.check("fresh contiguous publication", (sequence - previous) & 0xFFFFFFFF, 1)
        sample = {name: target.value("board_adc_reading." + name)
                  for name in ("vdda_mv", "temperature_mdeg_c", "quality")}
        target.record("adc.sample", dict(sample, sequence=sequence, index=index))
        target.check("expected provenance", sample["quality"], quality)
        target.check("plausible VDDA", 2800 <= sample["vdda_mv"] <= 3600, True)
        target.check("plausible temperature", -40000 <= sample["temperature_mdeg_c"] <= 125000, True)
        previous = sequence
    samples = [r["data"] for r in target.records("adc.sample")]
    target.check("complete series", len(samples), count)
    voltage = [s["vdda_mv"] for s in samples]
    temperature = [s["temperature_mdeg_c"] / 1000 for s in samples]
    target.record("adc.summary", dict(count=count, ddof=1,
        vdda_mv=dict(mean=mean(voltage), stdev=stdev(voltage)),
        temperature_c=dict(mean=mean(temperature), stdev=stdev(temperature))))
    target.check("samples and summary retained", len(target.records()), count + 1)
