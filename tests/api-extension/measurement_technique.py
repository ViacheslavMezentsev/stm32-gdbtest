"""TECH-011: configured acquisition, detached records and offline calculations."""
from measurement_series import summarize


def configured_series(t):
    """Pair for the existing E1 series; assumes its published-reading stop points."""
    settings = t.config['api']['user']['measurement']
    count, quality = settings['count'], settings['expected_quality']
    # Consumer parameters remain the scenario's responsibility.
    if type(count) is not int or not 2 <= count <= 100:
        raise ValueError('count must be an integer from 2 to 100')
    previous = None
    for _ in range(count):
        t.reach('board_adc_sample')
        t.reach('board_delay_ms')
        sequence = t.value('board_adc_sequences')
        if previous is not None:
            t.check('new ADC sequence', (sequence - previous) & 0xFFFFFFFF, 1)
        sample = {'sequence': sequence}
        for field in ('quality', 'vdda_mv', 'temperature_mdeg_c'):
            sample[field] = t.value('board_adc_reading.' + field)
        t.record('mcu.measurement', sample)
        t.check('measurement provenance', sample['quality'], quality)
        t.check('plausible VDDA', 2800 <= sample['vdda_mv'] <= 3600, True)
        t.check('plausible die temperature',
                -40000 <= sample['temperature_mdeg_c'] <= 125000, True)
        previous = sequence
    return summarize(t, expected_quality=quality), t.records()


def mean_in_gdb(values, gdb):
    """Fixed GDB expression over captured integers, no inferior reads or calls.

    Call only on the main GDB thread. Keep aggregate within signed 64-bit range
    for the tested ARM GDB builds. Scratch convenience variables are restored.
    Python mean is preferable unless GDB expression semantics are needed.
    """
    values = list(values)
    if not values or any(type(v) is not int for v in values):
        raise ValueError('nonempty integer measurements required')
    total, count = sum(values), len(values)
    if not -(1 << 63) <= total < (1 << 63) or count >= (1 << 63):
        raise ValueError('aggregate outside signed 64-bit range')
    names = ('ddtt_tech011_sum', 'ddtt_tech011_count')
    previous = [gdb.convenience_variable(name) for name in names]
    try:
        gdb.set_convenience_variable(names[0], gdb.Value(total))
        gdb.set_convenience_variable(names[1], gdb.Value(count))
        return float(gdb.parse_and_eval('(double)$ddtt_tech011_sum / $ddtt_tech011_count'))
    finally:
        for name, value in zip(names, previous):
            gdb.set_convenience_variable(name, value)
