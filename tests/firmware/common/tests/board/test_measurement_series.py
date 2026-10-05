"""
RU: Вариативная серия измерений: несколько публикаций ADC с продолжением между выборками.
EN: Varying measurement series: several ADC publications with continuation between samples.
"""
from stm32_gdbtest import case, within


# Length of the series: enough publications to show that every sample is new.
SAMPLES = 5
# Plausibility window of the die temperature in mdegC; not a calibration or accuracy claim.
PLAUSIBLE_DIE_MDEG_C = within(-40_000, 125_000)


# One publication per iteration: board_adc_sample fills the buffer, board_delay_ms closes it.
@case("HW_CI_MEASUREMENT_SERIES", labels=("api", "measurement"), contracts=("ci_app_api",))
def measurement_series(t):
    values = []
    sequences = []

    # One sample per published measurement; the sequence counter proves that each one is new.
    for index in range(SAMPLES):
        t.reach("board_adc_sample")
        t.reach("board_delay_ms")
        value = t.read("board_adc_reading.temperature_mdeg_c")
        sequence = t.read("board_adc_sequences")
        values.append(value)
        sequences.append(sequence)
        t.record("measurement.sample", {"value": value, "sequence": sequence, "index": index})

    # Real data with a strictly advancing publication counter.
    t.check("series length", len(values), SAMPLES)
    t.check("every sample is real data", all(value != 0 for value in values))
    t.check("publication counter advanced", sequences, sorted(sequences))
    t.check("publication counter is unique", len(set(sequences)), len(sequences))
    t.check("records kept every sample", len(t.records("measurement.sample")), SAMPLES)

    # The die temperature may stay on one value for the whole series, so equal samples are accepted.
    t.check("series minimum is plausible", min(values), PLAUSIBLE_DIE_MDEG_C)
    t.check("series maximum is plausible", max(values), PLAUSIBLE_DIE_MDEG_C)
