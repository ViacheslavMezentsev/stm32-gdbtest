"""Explicitly selected hardware experiment, outside normal board test discovery."""

from stm32_gdbtest import case
from measurement_series import f411_measurement_series


@case("HW_E1_MEASUREMENTS", timeout_s=60, contracts=("ci_adc_units",))
def measurements(target):
    summary, records = f411_measurement_series(target, count=10)
    # Harness-only transport to retain the experiment; not the record API contract.
    target.report["e1_evidence"] = {"summary": summary, "records": records}
