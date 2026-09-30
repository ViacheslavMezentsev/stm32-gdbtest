# F030 CMSIS: ADC/DMA and completion timeout

[Documentation](index.md) · [Русский](../ru/F030_CMSIS_ADC_DMA.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

2026-09-30, codex/f030-cmsis-adc-dma based on 5883316. NUCLEO-F030R8,
native ST-Link V2J45M31/SWD 1 MHz, OpenOCD0.12.0, Windows,
xPack GCC13.3.1-1.1/GDB14.2.90/Python3.11.4. USB/SWD only, no UART or
external analog signals. Implementation: tests/firmware/src/adc_f030.c.

## Migrated behaviour

ADC1: asynchronous HSI14, calibration with ADC disabled and DMA requests off,
12-bit forward scan of channels16/17 (temperature/VREFINT), 239.5 sampling
cycles, one software-started sequence per application iteration.
Internal sources and the post-calibration transition wait two SysTick edges,
guaranteeing at least one full millisecond regardless of tick phase.
DMA1 channel1: normal halfword transfer, MINC, two samples in SRAM, TC/TE IRQ9.
The handler publishes both raw samples before advancing board_adc_sequences.

HSI14/calibration/ADRDY/publication waits have a 20-SysTick-tick deadline.
board_adc_error codes: 1 clock, 2 calibration, 3 ready, 4 completion timeout,
5 DMA transfer error, 6 busy ADC. board_adc_fault stops DMA and remains in
WFI; no automatic retry. Deadlines depend on working SysTick; the external
runner timeout remains required.

## Checks and results

| Scenario | Evidence |
| --- | --- |
| HW_CI_ADC_INIT | Clock, CKMODE, scan, sampling, internal paths, calibration finished/ADEN, DMA addresses/format, NVIC and vector25 |
| HW_CI_ADC_DMA | Two sequences: IPSR25, TCIF without TEIF, CNDTR0, both raw values/sequence published, no overrun |
| HW_CI_ADC_TIMEOUT | IRQ9 disabled through logged NVIC mutation; DMA completes, publication0, error4 and board_adc_fault |

Final **9/9 HW PASS**, including the previous six scenarios; series
20260930T135918…20260930T135934. Observed raw pairs (1759,1519), (1758,1519)
are observations of this board, not exact physical expectations.
ELF SHA256: `9200ea94e66d7e69792336eca76f38a24158fbdfb1a63a16be220bf03e3b91ab`.
JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/;
logs: build/f030-cmsis-adc-dma/*-final.log. HAL firmware restored,
HW_BOOT PASS 20260930T135936, reset_run; MCU running.

The first run stopped at HW_CI_ADC_INIT: CFGR2 read 0x1000 rather than zero.
The test incorrectly included bits outside CKMODE. Checked against CMSIS F0
V1.11.6: ADC_CFGR2_CKMODE (31:30) selects the clock. Only the field assertion
was corrected; configuration was unchanged. FAIL and intermediate reports
are retained. Compare documented fields using CMSIS masks instead of assuming
all other register bits read zero. Tests do not read ADC DR.

## Limits and next steps

HW_ADC_DMA_INIT/RUNTIME map to CMSIS setup and real DMA publication.
HW_ADC_DMA_TIMEOUT maps to missing IRQ; HAL callback suppression and
HAL_ADC_Start_DMA error returns require a separate HAL fixture.
The other five failure codes, ADC accuracy, physical temperature/VDDA and
external channels are not tested. Next: F030 single-point calibration and
independent arithmetic vectors; do not read TS_CAL2 just because a common
header defines it. GDB halts prevent throughput/power conclusions.
F103/F411, core API and the original ten run_hw.py steps are unchanged.
New scenarios use regular CLI run --test and are included in CI prepare.

Initial Docker run: 10/13; F030 rejected by the strict translation-unit list after adding adc_f030.c. Expected sources extended only for F030; missing linker input diagnostics separated from source-list mismatch.

Validation: Windows host 96 (8 skips); F030 CTest 10/10; Linux rerun — docs and F030 × GCC13/14/15 6/6 PASS. F103/F411 × three GCC versions and Linux host passed in the initial run. The full matrix is evidenced by two runs, not one 13/13 run. Formatting and strict specification checks PASS. Git index archive extracted on a case-sensitive filesystem.
