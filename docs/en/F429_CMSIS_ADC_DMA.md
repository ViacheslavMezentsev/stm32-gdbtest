# F429 CMSIS: ADC, DMA, arithmetic and faults

[Documentation](index.md) · [Русский](../ru/F429_CMSIS_ADC_DMA.md)

2026-10-01, working tree codex/f429-cmsis-adc-dma based on main `7a261e8`.
STM32F429I-DISCO + built-in ST-Link/V2, CN1/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Continues the [baseline](F429_CMSIS_BASELINE.md).

## Configuration and expectation sources

ADC1 scans temperature CH18 and VREFINT CH17. PCLK2/2=8 MHz,
480 cycles (60 us), TSVREFE without VBAT, ADON/DMA/DDS; 2 ms power-up delay.
DMA2 stream0/channel0 transfers two halfwords into SRAM, normal/direct mode,
IRQ56/vector72. TC publishes raw values before the sequence counter; LIFCR clears flags.
The fixture does not use the F1 ADC calibration procedure.

Calibration was checked against CubeF4 V1.28.3 stm32f4xx_ll_adc.h: TS_CAL1/2
30/110C and VREFINT_CAL at 3.3 V at 0x1FFF7A2C/2E/2A.
The STM32F429xx conditional branch uses CH18 with temperature/VBAT routing;
VBAT is disabled. IRQ56 was checked against stm32f429xx.h and the consumer HAL profile.
Firmware uses CMSIS only; shared adc_convert_f4_factory is unchanged.
Quality2 denotes calibration provenance, not temperature accuracy.

Both halfwords must lie entirely within 0x20000000..0x2002FFFF.
CCM is excluded from the linker and inaccessible to DMA; the scenario checks
this independently of M0AR/symbol equality. The driver is adc_f429.c.

Following the HSI16 MHz baseline, ADC runs at8 MHz rather than the previous HAL4 MHz. DMA remains normal, but DDS is enabled; before each software trigger the driver reenables ADC DMA requests and sets NDTR=2. This validates a standalone CMSIS mechanism, not bitwise equality with the HAL configuration.

## Cases

| HW_CI_* | Evidence |
| --- | --- |
| ADC_INIT, ADC_DMA | Registers, SRAM, NVIC/vector; two natural scans and raw publication |
| ADC_UNITS | Factory provenance, plausible VDDA/temperature |
| ADC_VECTORS | Five independent analytic points: anchors, midpoint, negative temperature, VDDA compensation |
| ADC_INVALID | 19 inputs: zero/saturation/uint16 max, equal/reversed calibration, VDDA outside window; normal acquisition afterwards |
| ADC_TIMEOUT | Mask IRQ56: DMA completes without notification, error4 after ≥20 ticks |
| ADC_BUSY | Stream EN before sampling: DMA ownership guard, error6, not an active ADC indicator |
| ADC_DISABLED | Clear ADON: error3 without publication, not a forced HAL return code |

[TECH-001/002/006/007](TESTING_TECHNIQUES.md): macro context, natural IRQs,
state injection and arithmetic vectors. Original HAL init/runtime/units/timeout
checks are replaced by CMSIS checks; handles/callbacks/HAL return paths are not covered.
Physical DMA errors, OVR and stream-disable timeout are implemented but not injected.

## Results and reproduction

**15/15 HW PASS**, followed by **3/3 ADC_DMA PASS** after timeout/busy/disabled.
Original F429 HAL firmware restored, HW_BOOT/HW_BLINK PASS, MCU left running.
One sample: VDDA 2962 mV, temperature 29340 mC, quality2; this is not metrology.
Windows build and prepare/traceability16/16 PASS. No other boards were run; the shared converter was unchanged.

ELF SHA256: `f3b5cee2c155a90d8339decb6cb80a8ba13489f0a5ac9d50fa1898df157b73a8`.
Artifacts under build/f429-cmsis-adc-dma: f429-windows-full-20261001T143204Z/summary.json
and tested-source-hashes.json. The base SHA does not identify modified sources.
Use f429zi/f429zi-offline presets in tests/firmware and CLI run with an explicit stand.
External host timeout/recovery and full-image HW were not repeated in this group.
Next: RTC/Sleep/deadline/recovery; API/schemas/rc.2 tag remain unchanged.

This short series without USB errors does not remove the historical ST-Link/V2 limitation.

Local regression: Windows docs/host4/4 (98 unittests, 8 platform skips); Linux Docker format/host and 15 MCU/GCC combinations17/17 PASS. Logs: build/f429-cmsis-adc-dma/linux-source/build/ci; Windows: windows-docs-host.json/windows-host.log alongside. GitHub Docs/full Offline of the new SHA are checked after push, before land.
