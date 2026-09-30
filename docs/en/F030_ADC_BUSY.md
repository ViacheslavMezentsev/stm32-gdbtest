# F030: busy ADC rejection

[Documentation](index.md) · [Русский](../ru/F030_ADC_BUSY.md)

Branch codex/f030-adc-busy based on 5d09823, first in a three-branch batch.
Firmware and core unchanged. HW_CI_ADC_BUSY enables CONT and ADSTART before
board_adc_sample through logged MMIO writes, confirms ADSTART, then requires
board_adc_error=6 at board_adc_fault. Sequence and quality remain zero.
The stream is deliberately unconsumed; overrun is expected. Teardown reset_run
restores normal configuration. This tests busy hardware state, not a
HAL_ADC_Start_DMA return override; DMA faults and all hardware error causes are not covered.

NUCLEO-F030R8/ST-Link V2J45M31, SWD1MHz/OpenOCD0.12.0, GCC13/GDB14.2.90,
Windows: HW PASS 20260930T172928. Previous16 cases were not rerun on this branch.
Same ELF as the [RTC report](F030_CMSIS_RTC.md).
F030 build/prepare/traceability 18/18, Windows host96 (8 skips) PASS.
Report: tests/firmware/build/f030r8/hwtest/runs/; log: build/f030-fault-batch/adc-busy.log.
Next dependent branch: RTC deadline, followed by acceptance and HAL restoration.
