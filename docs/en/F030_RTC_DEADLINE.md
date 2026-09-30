# F030: RTC wait deadline

[Documentation](index.md) · [Русский](../ru/F030_RTC_DEADLINE.md)

Second batch branch: codex/f030-rtc-deadline based on codex/f030-adc-busy (`3ba9c26`).
Firmware/API unchanged. HW_CI_RTC_DEADLINE reaches rtc_wait at error=3 and sets
mask=0, making readiness false. With SysTick running it requires error3 after
at least1000 ticks, no app_loop progress or RTC events, and unchanged BDCR.
This tests the shared wait/error propagation, not a physical LSI failure,
all initialization stages or incompatible retained RTC clock source rejection.

The first run gave ERROR after successful error3/deadline checks: RCC was not
available at board_rtc_fault. The fix saves &RCC->BDCR in rtc_wait and reads
unsigned int at that address after the fault; the address is not hardcoded.
A macro contract at RTC_IRQHandler does not guarantee macro visibility at
every stop, especially within inline CMSIS code. The original report is retained.

NUCLEO-F030R8/ST-Link/SWD1MHz/OpenOCD0.12.0, Windows/GCC13/GDB14.2.90:
fixed HW PASS 20260930T173225. ADC_DMA and RTC_ALARM after reset_run PASS
20260930T173248/20260930T173250 on the same ELF. HAL restored, HW_BOOT PASS
20260930T173254, reset_run; MCU running.
F030 build and CTest19/19 PASS. Logs: build/f030-fault-batch/;
JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/.
No new complete18-case run; previous16 and ADC_BUSY have separate evidence
on the same ELF from the [RTC report](F030_CMSIS_RTC.md).
