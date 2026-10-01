# F429 CMSIS: RTC, Sleep, deadline and recovery

[Documentation](index.md) · [Русский](../ru/F429_CMSIS_RTC_SLEEP.md)

2026-10-01, working tree codex/f429-cmsis-rtc-sleep based on codex/f429-cmsis-adc-dma `52c49fd`.
STM32F429I-DISCO + ST-Link/V2, CN1/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. No UART or additional wiring.
Continues [baseline](F429_CMSIS_BASELINE.md) and [ADC/DMA](F429_CMSIS_ADC_DMA.md).
The base SHA does not identify modified code; API, schemas and rc.2 tag are unchanged.

## Implementation

F429 RTC uses a calendar and Alarm A, LSI and PRER127/249.
Expectations were checked against STM32F429xx CMSIS in CubeF4 V1.28.3 and the former HAL profile.
RTC/EXTI17 registers and IRQ41 match shared rtc_f4.c; its algorithm is unchanged.
F401/F411/F429 vectors are shared: RTC IRQ41/vector57 and DMA2 stream0 IRQ56/vector72.
F401/F411 are checked offline; hardware evidence is F429 only.
This branch depends on ADC/DMA52c49fd: land ADC/DMA first, then RTC/Sleep after its own CI.

The fixture owns the calendar: initialization sets its starting date/time and masks
Alarm A fields for an event every calendar second. No BDRST is used; an incompatible
existing source yields error2. DBP/LSIRDY/ALRAWF/INITF/RSF waits have1000 SysTick-tick
limits (error1/3/4/5/6). ALRAF uses rc_w0; EXTI PR uses W1C.
This does not verify clock accuracy or calendar retention across reset.

## Scenarios

| HW_CI_* | Evidence |
| --- | --- |
| RTC_INIT | LSI/PRER, Alarm A, RSF/INIT, EXTI17 rising, NVIC bank1 and vector57 |
| RTC_ALARM | Two natural exception57 entries with ALRAF/EXTI pending, event++ and thread resumption |
| RTC_DEADLINE | LSIRDY wait mask=0: error3 after ≥1000 ticks, backup configuration unchanged |
| SLEEP_SYSTICK | Both NVIC banks masked; exception15, interrupted PC after WFI; delay/ADC retained |
| SLEEP_TIM2 | Only IRQ28, SysTick stopped: exception44 after WFI, no tick advance; controls restored |

[TECH-002/003/005/008](TESTING_TECHNIQUES.md): CMSIS context, natural IRQ,
argument injection and bounded interrupted-frame unwind.
GDB may insert a signal trampoline; absent unwind is an error, not PASS.
ICSR address/mask are saved before entering app.c.

## Results

**20/20 HW PASS**, plus **5/5 PASS**: three ADC_DMA repeats after ADC injections and
RTC_ALARM/ADC_DMA after RTC_DEADLINE. HAL restored, HW_BOOT/HW_BLINK PASS.
A separate scenario reached app_loop, saved an entry marker and stalled in Python sleep.
External timeout produced expected ERROR/TimeoutExpired and reset_run (host recovery).
RTC_ALARM/ADC_DMA then passed; another HAL restore/boot/blink passed.
MCU was left running. DEV_ID0x419 and Flash2048 KiB match this specimen's profile.

ELF SHA256: `c15e52f39b4d8669bfe2a12c20db78b0b308c61be554381a70739fa30aa20956`.
Artifacts under build/f429-cmsis-rtc-sleep (not committed):

- f429-windows-full-20261001T151255Z/summary.json: 20 cases, five repeats, two restore checks;
- f429-windows-full-20261001T151430Z/recovery-summary.json: timeout, RTC/ADC and two restore checks;
- tested-source-hashes.json: source hashes; summaries reference JSON/JUnit/marker paths.

Windows build and prepare/traceability 21/21 PASS. Local Windows docs/host: 4/4 PASS
(98 host tests, 8 skipped). Linux Docker: 17/17 PASS — formatting, host
and five MCUs on GCC 13/14/15 (15 build/prepare combinations). This is offline regression;
hardware evidence from this series applies only to F429/OpenOCD on Windows.
Summaries: `build/f429-cmsis-rtc-sleep/windows-docs-host.json` and
`build/f429-cmsis-rtc-sleep/linux-source/build/ci/summary.json`.

## Reproduction and limits

Use f429zi/f429zi-offline presets in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f429zi/hwtest/session.json --test <ID> --stand <local.toml>`.
Select F429/OpenOCD explicitly. Repeat RTC/ADC after RTC_DEADLINE;
restore HAL with HW_BOOT/HW_BLINK in finally after the suite.

Sleep means ordinary WFI, not Stop/Standby, current or sleep-residency measurement.
RTC wakeup was not isolated separately. GDB halt affects timing.
Mask injection checks deadline logic, not a physical LSI failure; other RTC wait faults
and incompatible-source selection were not injected. No backup retention, LSI accuracy,
HAL callback, full-image or Linux HW evidence. Firmware deadlines need SysTick;
external host timeout is independent. Five CMSIS profiles now have hardware evidence;
final HAL→CMSIS review and F411-consumer migration remain pending;
this group does not authorize deleting consumer HAL profiles.
Published-SHA GitHub Docs/full Offline are checked separately before land.


No USB errors occurred in this series; a short PASS does not close the historical ST-Link/V2 limitation.
