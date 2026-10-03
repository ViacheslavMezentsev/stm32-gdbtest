# TECH-010/011: paired runs on three stands

[Research](index.md) · [Русский](../ru/techniques-three-boards.md)

2026-10-03. Owner-authorized hardware runs of prepared variants completed. Core
and production scenarios remain unchanged; configuration and record/records use
research facades. This validates techniques on hardware, not an integrated API extension.

## Stands and sequence

| Board / MCU | Probe / backend | TECH-010 | Prepare | HW |
| --- | --- | --- | ---: | ---: |
| Nucleo-F030R8 / STM32F030R8T6 | ST-Link / OpenOCD 0.12.0 | RTC init | 7/7 PASS | 7/7 PASS |
| WeAct BluePill-Plus / STM32F103C8T6 | J-Link CE / J-Link GDB Server 8.32 | TIM2 init | 7/7 PASS | 7/7 PASS |
| WeAct BlackPill / STM32F411CEU6 | ST-Link / OpenOCD 0.12.0 | ADC/DMA init | 7/7 PASS | 7/7 PASS |

Windows, SWD 1000 kHz, xPack GCC 13.3.1; GDB 14.2.90.20240526-git, Python 3.11.4.
CMSIS firmware from tests/firmware. Connections matched local TOML and the previously
agreed stand; USB presence was not treated as MCU identification.

Seven HW runs per board: original ADC units, original RTC/TIM2/ADC block, its table
variant, original E1 series, configured TECH-011 series, restoration BOOT/GPIO.
The same seven prepare checks preceded them. An additional preliminary prepare
passed on each board but is not added to the table. Each series has 10 samples.
Production runner handled server locking and flash=if-different without mass erase,
option bytes or shared mode. Every HW run confirmed image_verified and reset_run teardown.

Verified CMSIS images remain on F030/F103. Original consumer HAL firmware restored
on F411 with HW_BOOT/HW_GPIO PASS. No residual GDB servers found. Experimental ELF/
manifest and restored ELF hashes are in [sanitized JSON](../results/techniques-three-boards.json).
Local paths, serial numbers, ELF and full logs are not committed.

## Pair comparisons

The [verification/export script](../../../../tests/api-extension/summarize_techniques.py)
compared actual reports: TECH-010 checks matched the originals exactly on each board,
including labels, order, actual/expected and passed.

TECH-011 retained every original series check and added four: configuration MCU,
measurement quality and Python/GDB agreement for both means. Each journal has 10
raw samples plus summary. Python/GDB means use the same captured samples with a
1e-9 tolerance in final units. Measurements across sequential runs need not match.

| MCU | quality | Mean VDDA, mV | Sample stdev, mV | Mean temperature, °C | Sample stdev, °C |
| --- | ---: | ---: | ---: | ---: | ---: |
| F030 | 3 | 3307.2 | 1.032796 | 33.6014 | 0.128971 |
| F103 | 1 | 3313.4 | 0.843274 | 24.3798 | 0.107481 |
| F411 | 2 | 3302.2 | 1.135292 | 27.2132 | 0.182975 |

These are the new configured-series results, ddof=1. Quality meanings differ:
F030 single-point calibration, F103 typical parameters, F411 factory calibration.
This table cannot compare absolute sensor accuracy. GDB stops affect timing and
temperature; this is not uninterrupted acquisition at ADC sample rate.

## Boundaries and next step

Every F103 HW run retained the known warning: profile Flash 64 KiB, observed 128 KiB,
image fits both. Profile unchanged; tests do not establish exact die marking.

No HW ERROR/FAIL occurred in this cycle. Negative table, missing-sample, quality and
RecordError cases remain prior host evidence; no hardware faults were injected.
TECH-011 still reads research TOML from GDB: production runner/agent snapshot
transport is not integrated. Available Windows paths do not demonstrate SSH portability.

Before HW: Docker docs/host 5/5 PASS, research suite 88/88 PASS. Next: enforce and
test accepted api.toml upper bounds in the prototype, then consolidate remaining
integration checks. Core promotion needs separate authorization; paired scenarios
now have hardware evidence for later comparison with the actual extended Target.
