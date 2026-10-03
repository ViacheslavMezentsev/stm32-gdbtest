"""Explicitly selected hardware experiment, outside normal board test discovery."""

from stm32_gdbtest import case
from measurement_series import f411_measurement_series
from evidence import RecordingTarget
from scenario_variants import cmsis_adc_units
from board_config import settings


@case("HW_E1_MEASUREMENTS", timeout_s=60, contracts=("ci_adc_units",))
def measurements(target):
    summary, records = f411_measurement_series(target, count=10, expected_quality=settings(target)['quality'])
    # Harness-only transport to retain the experiment; not the record API contract.
    target.report["e1_evidence"] = {"summary": summary, "records": records}


@case("HW_E1_ADC_PAIR", contracts=("ci_adc_units",))
def adc_pair(target):
    t = RecordingTarget(target)
    cmsis_adc_units(t)
    target.report["e1_evidence"] = {"records": t.records()}
