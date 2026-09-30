# F030 CMSIS: RTC Alarm A

[Documentation](index.md) · [Русский](../ru/F030_CMSIS_RTC.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

2026-09-30, codex/f030-cmsis-rtc based on f494ab1. NUCLEO-F030R8,
native ST-Link V2J45M31/SWD 1 MHz, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90/Python3.11.4; no additional wiring.

## Implementation and method

The tests/firmware/src/rtc_f030.c example owns its RTC calendar. LSI uses
127/311 prescalers (approximately one second at nominal 40 kHz). Each boot
sets 00:00:00, January1 year00, Monday: a repeatable fixture epoch, not actual
time. No BDRST is issued. An existing non-LSI source produces error2 instead
of resetting the backup domain.

Alarm A masks all calendar fields and subseconds, producing an alarm each
calendar second. EXTI17 rising → IRQ2, vector18 → RTC_IRQHandler.
The handler clears ALRAF by writing0, EXTI PR17 by writing1, then publishes
a counter. CMSIS and [RM0360](https://www.st.com/resource/en/reference_manual/rm0360-stm32f0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf) were used; flag clearing was also
compared with the local CubeF0 V1.11.6 HAL RTC source. HAL is not linked.

DBP/LSIRDY/ALRAWF/INITF/RSF waits have a 1000 SysTick tick deadline.
board_rtc_error codes: 1 DBP, 2 incompatible source, 3 LSI, 4 ALRAWF,
5 INITF, 6 RSF. On failure IRQ is disabled and board_rtc_fault stays in WFI,
without automatic retry. The deadline requires SysTick; the runner's external
timeout remains necessary. Fault branches have not been injection-tested;
this is not evidence of complete RTC fault diagnosis.

HW_CI_RTC_INIT checks clocks, prescalers, alarm masks, synchronization,
EXTI/NVIC/vector and no error. HW_CI_RTC_ALARM waits for two natural entries
with IPSR18, ALRAF and PR17, checks the published counter and return to
app_loop. No software IRQ or calendar mutation by the test. ci_rtc_macros
checks ELF expressions before the server; CI includes both prepare cases.

## Evidence

**16/16 HW PASS** on the new ELF: two RTC cases and all previous fourteen.
RTC INIT: 20260930T165930; ALARM: 20260930T165945; regression:
20260930T170011–20260930T170049. JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/;
logs: build/f030-cmsis-rtc/.
ELF SHA256: `b911213338acc2de1b0d47a41d7c0b23a50974ba8f78370e041f2afbc2a00e9e`.
HAL restored, HW_BOOT PASS 20260930T170052, teardown reset_run.

## Limits and next step

Preserves configuration and natural IRQ evidence from HW_RTC_INIT/ALARM,
but not HAL callbacks/macros. Halt may coalesce events; the counter does not
guarantee every physical second is counted. LSI accuracy, long-term calendar
operation, rollover, VBAT retention, Stop/Standby and current are not proven.
GCC14/15 have build/prepare coverage only; HW evidence is for GCC13.

Next: fault scenarios and final HAL→CMSIS acceptance mapping. Sixteen cases
do not automatically replace all seventeen original cases.

Local checks: F030 build/CTest 17/17; Windows host 96 (8 skips); Linux Docker docs/host and nine firmware pairs (F030/F103/F411 × GCC13/14/15) — 13/13 PASS. C formatting and strict specification check PASS.
