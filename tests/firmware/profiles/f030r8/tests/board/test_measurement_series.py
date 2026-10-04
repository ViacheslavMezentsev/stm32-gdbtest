"""
RU: Вариативная серия измерений: несколько публикаций ADC с продолжением между выборками.
EN: Varying measurement series: several ADC publications with continuation between samples.
"""
from stm32_gdbtest import case

SAMPLES = 5
PLAUSIBLE_LOW = -40000
PLAUSIBLE_HIGH = 125000


# One publication per iteration: board_adc_sample fills the buffer, board_delay_ms closes it.
@case("HW_CI_MEASUREMENT_SERIES", labels=("api", "measurement"), contracts=("ci_app_api",))
def measurement_series(target):
    values = []
    sequences = []
    for index in range(SAMPLES):
        target.reach("board_adc_sample")
        target.reach("board_delay_ms")
        value = target.value("board_adc_reading.temperature_mdeg_c")
        sequence = target.value("board_adc_sequences")
        values.append(value)
        sequences.append(sequence)
        target.record("measurement.sample", {"value": value, "sequence": sequence, "index": index})

    # Real data with a strictly advancing publication counter.
    target.check("series length", len(values), SAMPLES)
    target.check("every sample is real data", all(value != 0 for value in values), True)
    target.check("publication counter advanced", sequences, sorted(sequences))
    target.check("publication counter is unique", len(set(sequences)), len(sequences))
    target.check("records kept every sample", len(target.records("measurement.sample")), SAMPLES)

    # The series must vary: a single repeated value would not exercise measurement statistics.
    target.check("series varies", len(set(values)) > 1, True)
    target.check("series inside the plausible domain",
                 all(PLAUSIBLE_LOW <= value <= PLAUSIBLE_HIGH for value in values), True)
