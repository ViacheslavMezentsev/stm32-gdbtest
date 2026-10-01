# F103 CMSIS: ADC, DMA, physical units and failures

[Documentation](index.md) · [Русский](../ru/F103_CMSIS_ADC_DMA.md)

2026-10-01, codex/f103-cmsis-adc-dma based on main 352417c. Working tree tested;
the base SHA is not claimed as the changed code SHA. WeAct BluePill-Plus F103C8,
J-Link 8.32/SWD, Windows, GCC 13.3.1-1.1/GDB 14.2.90. No UART/external wiring.
This group continues [clocks/GPIO/SysTick/TIM2](F103_CMSIS_BASELINE.md).

## Implementation

ADC1 uses PCLK2/2 = 4 MHz. Power-up is followed by 2 ms settling, RSTCAL and
CAL with separate 20 ms deadlines. Regular scan: CH16 (temperature), then
CH17 (VREFINT), 239.5 cycles each. TSVREFE settles for 2 ms.
EXTSEL=7/EXTTRIG/SWSTART starts a single sequence. DMA1 channel1 uses normal
mode: two halfwords into SRAM, IRQ 11/vector 27. DMA is enabled after calibration;
ISR publishes raw values before incrementing the counter. Each sample reloads
CNDTR; the handler disables DMA and clears flags.

Configuration source: [RM0008](https://www.st.com/resource/en/reference_manual/rm0008-stm32f103xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).
For calculations, [DS5319](https://www.st.com/resource/en/datasheet/stm32f103c8.pdf)
provides typical VREFINT=1.20 V, V25=1.43 V, slope=4.3 mV/°C.
Conversion uses raw ratios, int64 and libgcc; application window 2400–3600 mV.
`quality=1` means TYPICAL, not factory calibration or 0.001 °C accuracy.
No F030/F411 calibration addresses are read. The formula and four analytic
vectors preserve the consumer's adc_convert_typical approach; module core unchanged.

## Checks

| New scenarios | Evidence |
| --- | --- |
| ADC_INIT | Clocks, CR1/CR2, ranks/sample time, DMA buffer/configuration, NVIC/vector |
| ADC_DMA | Two natural sequences, exception 27/TC without TE, publication and DMA stop |
| ADC_UNITS | TYPICAL and plausible real measurement range |
| ADC_VECTORS | Four fixed vectors: 25, -25, 100 °C and VDDA scaling |
| ADC_INVALID | Eight invalid input sets, then normal acquisition |
| ADC_TIMEOUT | ICER IRQ 11: DMA completes without notification, error 4 after ≥20 ticks |
| ADC_BUSY | DMA EN before sample: error 6 without publication; channel ownership guard |
| ADC_DISABLED | ADON=0 before sample: error 3 without publication |

Full IDs have the HW_CI_ prefix. TECH-001/002 apply to CMSIS context;
[TECH-006/007](TESTING_TECHNIQUES.md) to MMIO and arithmetic arguments.
Contracts check macro context in adc_f103.c and the adc_convert_f103 signature.

**15/15 HW PASS**, including the seven previous scenarios. After each of three
hardware-state injections, ADC_DMA was repeated separately: **3/3 PASS**.
Original consumer HAL firmware restored, HW_BOOT/HW_BLINK PASS, reset_run;
board left running. Example reading: 3313 mV, 28809 m°C, quality 1; this is not
an independent metrology check.

ELF SHA256: `39cbb960bb62fcb65b1bf9c962b272997270de2abc63ca16723774f525a12b20`.
Local evidence: build/f103-cmsis-adc-dma/
f103-windows-full-20261001T082723Z/summary.json; JSON/JUnit:
tests/firmware/build/f103c8/hwtest/runs. Summary links each result.

## Limits and reproduction

F1 lacks F0 ADSTART: DMA EN does not prove an active ADC conversion. ADC_BUSY
checks only the stated ownership guard; IRQ masking does not simulate a broken
analog input. TE/error 5 and RSTCAL/CAL deadlines are implemented but were not
injected in this group. No claim of sensor accuracy, DMA throughput, lossless
continuous streaming or HAL handles/callbacks/return-code coverage.
F103 has no F0 OVR flag; that evidence is not carried over. GDB halt affects
timing; ADC_DR reads have side effects, so scenarios inspect SRAM instead.
RTC/Sleep is the next group; pack/full-image lifecycle was not repeated here.

Build/prepare: f103c8 and f103c8-offline presets from tests/firmware.
Run each hardware ID from the module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f103c8/hwtest/session.json --test <ID> --stand <local.toml>`.
Use the BluePill/J-Link stand; validate the consumer restore-session beforehand,
repeat ADC_DMA after fault cases, restore HAL and boot/blink in finally.

Local regression: Windows docs/host 4/4, F103 CTest 16/16; Linux Docker host
and nine F030/F103/F411 × GCC13/14/15 combinations — 10/10 stages PASS.
Includes prepare, negative contracts and image policy. Logs:
build/f103-cmsis-adc-dma/linux-source/build/ci. C formatting PASS.
GitHub CI follows push separately; other boards were not hardware-tested.
