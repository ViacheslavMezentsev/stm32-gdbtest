# F411 CMSIS: ADC/DMA, factory calibration and failures

[Documentation](index.md) · [Русский](../ru/F411_CMSIS_ADC_DMA.md)

2026-10-01, working tree codex/f411-cmsis-adc-dma based on main cb17bdf.
WeAct BlackPill F411CE + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. No UART/external wiring.
Continues [baseline](F411_CMSIS_BASELINE.md); API/schemas and rc.2 tag are unchanged.
The base SHA does not identify the modified implementation.

## Implementation

ADC1 uses PCLK2/2=8 MHz, scan CH18 temperature then CH17 VREFINT,480 cycles each.
TSVREFE is enabled, VBAT disabled, with2 ms settling after ADON; no F1 RSTCAL/CAL.
Configuration reference:
[RM0383](https://www.st.com/resource/en/reference_manual/dm00119316-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).

DMA2 Stream0/channel0, normal/direct mode, two SRAM halfwords, MINC,
TC/TE/DME interrupts, IRQ56/vector72. Hardware stops the stream at NDTR=0.
The ISR clears flags via LIFCR W1C and publishes raw values before sequence.
Each sample reloads NDTR, clears ADC SR and toggles ADC DMA; DDS retains requests
between sequences, SWSTART launches the scan. Stream disable during init and
completion notification have20-tick deadlines. Busy-stream guard=error6, ADON0=error3,
notification timeout=error4, DMA errors=error5, post-completion OVR=error7.

Factory addresses from [DS10314](https://www.st.com/resource/en/datasheet/stm32f411ce.pdf):
VREFINT_CAL=0x1FFF7A2A, TS_CAL1=0x1FFF7A2C, TS_CAL2=0x1FFF7A2E,
at3.3 V and30/110 C. These belong to the F411 fixture, not the generic core.
Pure adc_convert_f411 takes five uint16 arguments; int64/libgcc retain precision
of intermediate raw/calibration ratios. quality2 means FACTORY, not metrological accuracy.
The2400–3600 mV window is application-specific. Equal/reversed anchors, zero/saturated
codes and invalid supply produce a zero reading.

## Scenarios and result

| HW_CI_* | Check |
| --- | --- |
| ADC_INIT | Clocks, ranks/sample times, stream configuration/addresses, NVIC/vector |
| ADC_DMA | Two natural scans, exception72, TC without TE/DME/FE, publication/stream stop |
| ADC_UNITS | Factory provenance, plausible VDDA/temperature |
| ADC_VECTORS | Five independent anchors:30/110/70/-10 C and changed VDDA |
| ADC_INVALID | 15 invalid raw/calibration arguments +4 ordering/supply cases; normal recovery |
| ADC_TIMEOUT | IRQ56 masked: NDTR0 without publication; error4 after ≥20 ticks |
| ADC_BUSY | EN before sample: ownership guard error6 without publication |
| ADC_DISABLED | ADON0: error3 without publication |

**15/15 HW PASS**, including seven baseline scenarios. ADC_DMA was repeated after
each of three state injections: **3/3 PASS**. Consumer HAL restored,
HW_BOOT/HW_BLINK PASS, reset_run, MCU running. Example:3300 mV,28103 mC,quality2.
F030/F103 hardware was not exercised.

ELF SHA256: `f590213d360c8952fef7e88aec2bc0b9fe547099c26483b1928690f8999e1853`.
Local evidence: build/f411-cmsis-adc-dma/f411-windows-full-20261001T113100Z/summary.json;
linked JSON/JUnit, sources in tested-source-hashes.json. Artifacts are Git-ignored.
Windows prepare/traceability:16/16 PASS.

## Limits and reproduction

[TECH-001/002/006/007](TESTING_TECHNIQUES.md): CMSIS context in adc_f411.c,
MMIO injection and pure-arithmetic argument replacement. IRQ56 uses NVIC bank1.
DMA EN is not F0 ADSTART and does not prove an active conversion. DMA errors,
OVR and stream-disable timeout are implemented but not injected. No metrology,
continuous throughput, external analog inputs or HAL callback/return-code evidence.
GDB halt changes timing; tests read SRAM rather than ADC_DR.

Build/prepare: f411ce/f411ce-offline presets in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f411ce/hwtest/session.json --test <ID> --stand <local.toml>`.
Select F411/OpenOCD explicitly; repeat ADC_DMA after injection, restore HAL and check
HW_BOOT/HW_BLINK in finally. Next group: RTC/Sleep/recovery.
GitHub Docs/Offline are checked after push; consumer gitlink is not updated yet.

Local Windows docs/host4/4 (98 unittests,8 platform skips), C/H format PASS.
Linux Docker host and nine MCU/GCC combinations:10/10 PASS; logs under
build/f411-cmsis-adc-dma/linux-source/build/ci. Offline evidence, not Linux HW.
