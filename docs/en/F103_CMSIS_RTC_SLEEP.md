# F103 CMSIS: RTC, Sleep, deadlines and recovery

[Documentation](index.md) · [Русский](../ru/F103_CMSIS_RTC_SLEEP.md)

2026-10-01, working tree codex/f103-cmsis-rtc-sleep based on main 3e123ad.
WeAct BluePill-Plus F103C8, J-Link 8.32/SWD, Windows,
GCC 13.3.1-1.1/GDB 14.2.90; no UART or external connections.
Continues [baseline](F103_CMSIS_BASELINE.md) and [ADC/DMA](F103_CMSIS_ADC_DMA.md).
The base SHA is not the modified source SHA. Module API and schemas are unchanged.

## F1 RTC and migration boundaries

[RM0008](https://www.st.com/resource/en/reference_manual/rm0008-stm32f103xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
describes a 32-bit counter, 20-bit prescaler and Alarm comparator.
F103 has no F030 calendar, PRER/ALRMAR or write-protection sequence.
The fixture selects LSI, PRL=39999 (nominal 1 s at 40 kHz), resets the counter
to zero and sets the initial alarm to2. It owns the counter and discards prior time,
but never performs BDRST. A different existing RTC clock source is refused with error2.

RSF synchronizes APB shadows; RTOFF is checked before/after CNF configuration.
Waits are bounded by1000 firmware ticks: error1=DBP, 3=LSIRDY, 4=RSF,
5=write readiness, 6=write completion. CRL flags use rc_w0 while preserving
other flags and keeping CNF=0; EXTI17 PR uses W1C, not read-modify-write.

Alarm uses EXTI17 rising, IRQ41/vector57; global RTC IRQ3 is disabled.
The ISR clears flags, increments board_rtc_events and requests rearming.
Thread-mode board_rtc_service reads coherent CNTH/CNTL and schedules counter+2.
Write waits stay outside the ISR so lower-priority SysTick can provide deadlines.
This is a periodic notification delayed by main-loop servicing, not a precise
two-second scheduler. Long GDB stops change its timing.

## Scenarios and evidence

| HW_CI_* scenario | Evidence |
| --- | --- |
| RTC_INIT | LSI, PRL, initial alarm, RSF/RTOFF/CNF, EXTI17, NVIC and vector57 |
| RTC_ALARM | Two natural IRQ57 entries with ALRF/EXTI pending, one event per IRQ, rearm and thread resumption |
| RTC_DEADLINE | LSIRDY rtc_wait mask=0: error3 after ≥1000 ticks; backup configuration retained |
| SLEEP_SYSTICK | Both external NVIC banks disabled; exception15, interrupted PC following WFI |
| SLEEP_TIM2 | Only IRQ28, SysTick disabled: exception44 following WFI, no tick advance, controls restored |

Sleep checks use GDB unwind, bounded attempts and saved interrupted_contexts.
They verify ordinary Sleep, not Stop/Standby or current consumption.
Macro context comes from the corresponding CMSIS translation unit; the ICSR
address is saved before entering HAL-free app.c. See [TECH-002/003/005/008](TESTING_TECHNIQUES.md).

**20/20 HW PASS**, including the previous regression; **5/5 positive repeats**:
ADC_DMA after three ADC injections, RTC_ALARM/ADC_DMA after RTC_DEADLINE.
The first harness summary is ERROR: Windows sandbox ACL denied the HAL restore
report directory. Relocating output revealed a second denial for the existing
probe-lock. Both happened before MCU connection and are retained.
A separate restore with required access passed HW_BOOT/HW_BLINK.

An additional scenario reached app_loop, wrote an entry marker and deliberately
stalled in Python sleep. External timeout produced the expected ERROR/TimeoutExpired
and `reset_run (host recovery)`; subsequent RTC_ALARM and ADC_DMA passed.
HAL was restored again, HW_BOOT/HW_BLINK passed; the MCU was left running.

ELF SHA256: `07647c3c0bac19367645325c61ffc5886c648e04f8f0d15f463a4a94fbcf1315`.
Local artifacts under build/f103-cmsis-rtc-sleep:
- f103-windows-full-20261001T103058Z/summary.json: 25 PASS, restore error;
- f103-windows-full-20261001T103225Z/restore-summary.json: lock access error;
- f103-windows-full-20261001T103241Z/restore-summary.json: successful restore;
- f103-windows-full-20261001T103317Z/recovery-summary.json: timeout/recovery and final restore.

JSON/JUnit and marker paths are retained in summaries. tested-source-hashes.json
records the source snapshot; build artifacts are Git-ignored.

## Reproduction and limits

Use presets f103c8 and f103c8-offline in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f103c8/hwtest/session.json --test <ID> --stand <local.toml>`.
Select BluePill/J-Link explicitly. Repeat RTC_ALARM/ADC_DMA after RTC_DEADLINE;
restore consumer HAL and check HW_BOOT/HW_BLINK in finally after the suite.

The mask injection checks deadline logic, not a physical LSI fault.
RSF/RTOFF/DBP and incompatible clock-source failures were not injected; backup
retention, counter rollover, LSI accuracy and RTC-specific Sleep wakeup remain unverified.
Firmware deadlines require SysTick; host timeout is a separate protection layer.
This does not prove HAL callbacks/return codes or replace the HAL techniques.
Pack/full-image and Linux HW were not repeated; no other boards were exercised.

Windows prepare/traceability: 21/21 PASS, docs/host: 4/4 (98 unittests,
8 platform skips). Linux Docker host and nine F030/F103/F411 × GCC13/14/15
combinations: 10/10 stages PASS; logs in linux-source/build/ci under the experiment directory.
Owned C/H formatting: PASS. GitHub Docs/Offline are checked after push.
