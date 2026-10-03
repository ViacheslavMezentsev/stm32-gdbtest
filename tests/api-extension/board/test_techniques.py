"""Explicit TECH-010/011 board variants, outside production discovery."""
from pathlib import Path

from stm32_gdbtest import case
from board_config import settings
from evidence import RecordingTarget
from measurement_technique import configured_series, mean_in_gdb
from session_config import load_session
from session_pipeline import ConfiguredTarget
from table_variants import f030_rtc, f103_timer, f411_adc


@case('HW_TECH010_F030', contracts=('ci_rtc_macros',))
def table_f030(target):
    f030_rtc(target)


@case('HW_TECH010_F103', contracts=('ci_timer_macros',))
def table_f103(target):
    f103_timer(target)


@case('HW_TECH010_F411', contracts=('ci_adc_macros',))
def table_f411(target):
    f411_adc(target)


@case('HW_TECH011_SERIES', timeout_s=60, contracts=('ci_adc_units',))
def configured_measurements(target):
    import gdb
    profile = {'STM32F030R8T6': 'f030r8', 'STM32F103C8T6': 'f103c8',
               'STM32F411CEU6': 'f411ce'}[target.profile['mcu']]
    # Core acceptance uses the runner's captured configuration and actual Target.
    # The historical prototype path remains available for paired comparison.
    integrated = target.config_props['api'] is not None
    snapshot = target if integrated else load_session(Path(__file__).resolve().parents[1]/'config'/profile/'session.toml')
    target.check('configuration matches MCU', snapshot.config['target']['mcu'], target.profile['mcu'])
    target.check('configured measurement quality',
                 snapshot.config['api']['user']['measurement']['expected_quality'], settings(target)['quality'])
    t = target if integrated else RecordingTarget(ConfiguredTarget(target, snapshot), **snapshot.config['api']['records'])
    summary, records = configured_series(t)
    samples = [r['data'] for r in records if r['name'] == 'mcu.measurement']
    voltage = mean_in_gdb([s['vdda_mv'] for s in samples], gdb)
    temperature = mean_in_gdb([s['temperature_mdeg_c'] for s in samples], gdb) / 1000
    target.check('GDB/Python VDDA mean', abs(voltage-summary['vdda']['mean']) < 1e-9, True)
    target.check('GDB/Python temperature mean', abs(temperature-summary['temperature']['mean']) < 1e-9, True)
    # Harness export, not part of the record API.
    target.report['tech011_evidence'] = dict(summary=summary, records=records,
                                            gdb_means=dict(vdda_mv=voltage, temperature_c=temperature))
    target.report['integrated_api'] = integrated
