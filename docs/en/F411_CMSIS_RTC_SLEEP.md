# F411 CMSIS: RTC, Sleep, deadline and recovery

[Documentation](index.md) · [Русский](../ru/F411_CMSIS_RTC_SLEEP.md)

2026-10-01, working tree codex/f411-cmsis-rtc-sleep based on main4a6f5d3.
WeAct BlackPill F411CE + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. No UART/external wiring.
Continues [baseline](F411_CMSIS_BASELINE.md) and [ADC/DMA](F411_CMSIS_ADC_DMA.md).
The base SHA does not identify modified code; API/schemas/rc.2 tag are unchanged.

## Implementation

Unlike the F103 counter, F411 uses a calendar and Alarm A. Nominal LSI32 kHz,
PRER127/249; reference:
[RM0383](https://www.st.com/resource/en/reference_manual/dm00119316-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).
The fixture owns the calendar: init sets its time/date and masks all Alarm A fields
for an event every calendar second. This is not an accurate external second
or calendar-retention evidence.

No BDRST is used; an incompatible existing RTC source yields error2.
DBP/LSIRDY/ALRAWF/INITF/RSF waits have1000 SysTick-tick deadlines (error1/3/4/5/6).
WPR is unlocked during configuration and relocked afterwards.
ALRAF uses rc_w0 while preserving other flags and keeping INIT=0;
EXTI17 PR uses W1C without read-modify-write. IRQ41/vector57 publishes events.
Unlike F103, per-alarm software rearming is unnecessary.

## Scenarios

| HW_CI_* | Evidence |
| --- | --- |
| RTC_INIT | LSI/PRER, Alarm A, RSF/INIT, EXTI17 rising, NVIC bank1 and vector57 |
| RTC_ALARM | Two natural exception57 entries with ALRAF/EXTI pending, event++ and thread resumption |
| RTC_DEADLINE | LSIRDY wait mask=0: error3 after ≥1000 ticks, backup configuration unchanged |
| SLEEP_SYSTICK | Both NVIC banks masked; exception15, interrupted PC after WFI; delay/ADC retained |
| SLEEP_TIM2 | Only IRQ28, SysTick stopped: exception44 after WFI, no tick advance; controls restored |

[TECH-002/003/005/008](TESTING_TECHNIQUES.md): CMSIS frame, natural IRQ,
argument injection and bounded interrupted-frame unwind. GDB may insert a signal
trampoline; absent unwind is an error, not PASS. ICSR address/mask are saved
before entering app.c, where CMSIS macros are unavailable.

## Result

**20/20 HW PASS**; three ADC_DMA repeats after ADC injections and RTC_ALARM/ADC_DMA
after RTC_DEADLINE: another **5/5 PASS**. HAL restored, HW_BOOT/HW_BLINK PASS.
A separate scenario reached app_loop, saved an entry marker and stalled in Python sleep.
External timeout produced expected ERROR/TimeoutExpired and reset_run (host recovery).
RTC_ALARM/ADC_DMA then passed, followed by another HAL restore/boot/blink PASS.
The MCU was left running; no other boards were exercised.

ELF SHA256: `6411cb5136564a1b2cd6a167c1de5017d30ef0080d63efd600bd28a1391427dc`.
Local artifacts under build/f411-cmsis-rtc-sleep:
- f411-windows-full-20261001T114734Z/summary.json: full suite, repeats and restore;
- f411-windows-full-20261001T114912Z/recovery-summary.json: external timeout/recovery;
- tested-source-hashes.json: source snapshot. JSON/JUnit/marker paths are in summaries.

Windows prepare/traceability21/21 PASS. Artifacts are not committed.

## Reproduction and limits

Use f411ce/f411ce-offline presets in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f411ce/hwtest/session.json --test <ID> --stand <local.toml>`.
Select F411/OpenOCD explicitly, repeat RTC/ADC after RTC_DEADLINE, and restore HAL
with HW_BOOT/HW_BLINK in finally after the suite.

Sleep means ordinary WFI, not Stop/Standby, current or residency measurement.
RTC wakeup was not isolated separately. GDB halt affects calendar and delay timing.
Mask injection checks deadline logic, not physical LSI failure; other RTC wait faults
and incompatible-source selection were not injected. No backup retention, LSI accuracy
or HAL callback evidence. Firmware deadlines require SysTick; host timeout is independent.
Pack/full-image and Linux HW were not repeated. After land: review the three CMSIS
fixtures and update the consumer gitlink; old HAL profiles are not yet approved for deletion.
Published-SHA CI is checked separately.

Local regression: Windows docs/host4/4 (98 unittests,8 platform skips),
C/H format PASS; Linux Docker host and nine MCU/GCC combinations10/10 PASS.
Logs: build/f411-cmsis-rtc-sleep/linux-source/build/ci.
