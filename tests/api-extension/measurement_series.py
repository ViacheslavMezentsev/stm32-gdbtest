"""E1 consumer technique: Python statistics on published F411 CMSIS readings."""

from statistics import mean, stdev

from evidence import RecordingTarget


def summarize(t):
    """Summarize one scenario journal; sample standard deviation uses N-1."""
    samples = [r["data"] for r in t.records("mcu.measurement")]
    if len(samples) < 2:
        raise ValueError("at least two measurements are required")
    if len({s["sequence"] for s in samples}) != len(samples):
        raise ValueError("duplicate measurement sequence")
    if not all(s["quality"] == 2 for s in samples):
        raise ValueError("invalid measurement quality")
    voltages = [s["vdda_mv"] for s in samples]
    temperatures = [s["temperature_mdeg_c"] / 1000.0 for s in samples]
    result = {
        "count": len(samples),
        "vdda": {"unit": "mV", "mean": mean(voltages), "stdev": stdev(voltages)},
        "temperature": {"unit": "degC", "mean": mean(temperatures),
                        "stdev": stdev(temperatures)},
        "stdev_ddof": 1,
    }
    t.record("mcu.summary", result)
    return result


def f411_measurement_series(target, count=10):
    """Call from a GDB scenario with its Target; no automatic hardware execution.

    Requires the existing CMSIS F411 fixture and its factory-calibration quality=2.
    Stops at published readings; this does not measure uninterrupted acquisition.
    """
    if type(count) is not int or not 2 <= count <= 100:
        raise ValueError("count must be an integer from 2 to 100")
    t = RecordingTarget(target)
    previous = None
    for _ in range(count):
        t.reach("board_adc_sample")
        t.reach("board_delay_ms")
        sequence = t.value("board_adc_sequences")
        if previous is not None:
            t.check("new ADC sequence", (sequence - previous) & 0xFFFFFFFF, 1)
        sample = {"sequence": sequence}
        for field in ("quality", "vdda_mv", "temperature_mdeg_c"):
            sample[field] = t.value("board_adc_reading." + field)
        t.record("mcu.measurement", sample)
        t.check("factory provenance", sample["quality"], 2)
        t.check("plausible VDDA", 2800 <= sample["vdda_mv"] <= 3600, True)
        t.check("plausible die temperature",
                -40000 <= sample["temperature_mdeg_c"] <= 125000, True)
        previous = sequence
    summary = summarize(t)
    return summary, t.records()
