"""E2 observations on the existing F411 fixture; not a public Target extension."""

from stm32_gdbtest import case
from typed_read import Reader, GdbBackend, ReadError


@case("HW_E2_READ", contracts=("ci_adc_units",))
def read_snapshots(t):
    reader = Reader(GdbBackend(), ram_ranges=((0x20000000, 0x20020000),))
    t.reach('board_adc_sample')
    t.reach('board_delay_ms')
    snapshot = reader.read('board_adc_reading', fields=('vdda_mv', 'temperature_mdeg_c', 'quality'))
    values = {name: field.value for name, field in snapshot.value}
    for name, value in values.items():
        t.check('same scalar: ' + name, value, t.value('board_adc_reading.' + name))
    t.check('factory provenance', values['quality'], 2)
    t.check('plausible VDDA', 2800 <= values['vdda_mv'] <= 3600, True)
    t.check('plausible die temperature', -40000 <= values['temperature_mdeg_c'] <= 125000, True)
    samples = reader.read('board_adc_buffer', count=2)
    raw = [field.value for _, field in samples.value]
    t.check('same buffer', raw, [t.value(f'board_adc_buffer[{i}]') for i in range(2)])
    failures = {}
    for path, options in (('board_adc_sample()', {}), ('e2_missing_symbol', {}),
                          ('board_adc_buffer', {'count':3})):
        try:
            reader.read(path, **options)
        except ReadError as exc:
            failures[path] = exc.code
    t.check('negative read outcomes', failures,
            {'board_adc_sample()':'invalid_path', 'e2_missing_symbol':'missing_symbol',
             'board_adc_buffer':'array_bounds'})
    t.reach('board_adc_sample')
    t.check('snapshot retained after resume', {n: f.value for n, f in snapshot.value}, values)
    t.report['e2_evidence'] = {'values':values, 'raw':raw, 'errors':failures,
                              'types':{n:f.type_name for n,f in snapshot.value}}
