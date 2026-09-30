# F030 CMSIS: ADC physical units

[Documentation](index.md) · [Русский](../ru/F030_CMSIS_ADC_UNITS.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

2026-09-30, codex/f030-cmsis-adc-units based on a6c0426. NUCLEO-F030R8,
native ST-Link V2J45M31/SWD 1 MHz, OpenOCD0.12.0, Windows,
xPack GCC13.3.1-1.1/GDB14.2.90/Python3.11.4. No UART/external signals.

## Implementation

Pure adc_convert_f030 in tests/firmware/src/adc_units.c receives temperature/
VREFINT raw samples and two calibration words as arguments. No MMIO reads.
The adc_f030.c adapter reads F030 VREFINT_CAL (0x1FFFF7BA) and TS_CAL1
(0x1FFFF7B8), converts after DMA, and publishes board_adc_reading. No TS_CAL2.
Addresses checked against installed CubeF0 V1.11.6 LL header; model: DS9773,
30C/3.3V, typical negative slope 4.3mV/C.

VDDA = 3300 × reference_cal / reference in mV. Temperature uses the raw/
reference ratio without intermediate VDDA rounding. The 64-bit expression
uses C division truncating toward zero. For four inputs in 1..4094 the
intermediate numerator fits int64_t. Quality 3 means one factory point and
a typical slope, not two-point calibration or an accuracy claim.
Zero/saturation/above12bit inputs or VDDA outside the application's 2400..3600mV
window return all-zero fields (quality 0), replacing the previous reading.

Cortex-M0 division needs libgcc, linked explicitly for F030 only from the
same ARM GCC as the firmware. No libc/HAL added. Tests read board_adc_reading
after conversion returns, not during a structure update; atomic publication
is not claimed.

## Scenarios

- HW_CI_ADC_UNITS: real raw/factory words, quality 3, VDDA 2800..3600mV,
  temperature -40..125C. Plausibility, not metrology.
- HW_CI_ADC_VECTORS: seven fixed vectors by GDB argument mutation in the actual
  conversion: 30C/3300mV, 30C/3000mV, +/-100 counts, negative temperature,
  VDDA 2400/3600mV endpoints. Expected 30000, 48740, 11260, -44963 milliCelsius
  values are literals, not derived by executing the firmware as an oracle.
- HW_CI_ADC_INVALID: 0/4095/65535 in each of four arguments plus two
  out-of-window supply cases (14 vectors); all fields clear and a subsequent
  real acquisition restores quality 3. Mutations are logged.

This preserves F030 HW_ADC_UNITS/INVALID/VECTORS evidence independently of
HAL. No test hooks or GDB inferior function calls: stop on the real execution
path, mutate arguments, continue. CI prepare checks function/field contracts
but does not execute arithmetic. Numeric results here are demonstrated on
ARM hardware/GCC13; GCC14/15 are build/preflight checks, not HW vector runs.

## Result

**12/12 HW PASS**, series 20260930T151440…20260930T151507; ELF SHA256:
`cd52b5cbac535952fb4069b067c9e24bf536172126c0a98bdd40548a89e3e01b`.
This board measured 3308 mV, 34566 milliCelsius, quality 3. Integer representation
does not imply 0.001 C sensor accuracy/resolution.
Reports: tests/firmware/build/f030r8/hwtest/runs/; logs: build/f030-cmsis-adc-units/.
HAL restored: HW_BOOT PASS 20260930T151518, reset_run; MCU running.
Core API/F103/F411/run_hw.py unchanged. Next: RTC/Sleep and remaining failures;
CI optimization remains deferred until example migration.

Local checks: F030 CTest 13/13; Windows host 96 (8 skips); Linux Docker docs/host and F030/F103/F411 × GCC13/14/15 — 13/13 stages PASS. Git index archive extracted on a case-sensitive filesystem. Formatting and strict specification checks PASS.
