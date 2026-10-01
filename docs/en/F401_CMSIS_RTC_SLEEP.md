# F401 CMSIS: RTC, Sleep, deadline and recovery

[Documentation](index.md) · [Русский](../ru/F401_CMSIS_RTC_SLEEP.md)

2026-10-01, working tree codex/f401-cmsis-rtc-sleep based on main `87a23be`.
WeAct BlackPill v3.0 STM32F401CCU6 + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. No UART or additional wiring.
Continues [baseline](F401_CMSIS_BASELINE.md) and [ADC/DMA](F401_CMSIS_ADC_DMA.md).
The base SHA does not identify modified code; API, schemas and rc.2 tag are unchanged.

## Implementation

F401 RTC uses a calendar and Alarm A. Nominal LSI is32 kHz, PRER127/249;
expectations come from [RM0368](https://www.st.com/resource/en/reference_manual/DM00096844.pdf)
and STM32F401xC CMSIS in CubeF4 V1.28.3. RTC registers, EXTI17 and IRQ41 match
those used for F411: rtc_f411.c was moved to shared rtc_f4.c.
F401/F411 vectors are shared: RTC IRQ41/vector57 and DMA2 stream0 IRQ56/vector72.
F411 was checked offline after this change; new hardware evidence covers F401 only.

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
MCU was left running. DEV_ID0x423 and Flash256 KiB match this specimen's profile.

ELF SHA256: `9d9ab4ac8f8593be5bdfcacac3493e6f81bb66309fb8d258f8d764dc25047830`.
Artifacts under build/f401-cmsis-rtc-sleep (not committed):

- f401-windows-full-20261001T134226Z/summary.json: 20 cases, five repeats, two restore checks;
- f401-windows-full-20261001T134412Z/recovery-summary.json: timeout, RTC/ADC and two restore checks;
- tested-source-hashes.json: source hashes; summaries reference JSON/JUnit/marker paths.

Windows build and prepare/traceability21/21 PASS.

## Reproduction and limits

Use f401cc/f401cc-offline presets in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f401cc/hwtest/session.json --test <ID> --stand <local.toml>`.
Select F401/OpenOCD explicitly. Repeat RTC/ADC after RTC_DEADLINE;
restore HAL with HW_BOOT/HW_BLINK in finally after the suite.

Sleep means ordinary WFI, not Stop/Standby, current or sleep-residency measurement.
RTC wakeup was not isolated separately. GDB halt affects timing.
Mask injection checks deadline logic, not a physical LSI failure; other RTC wait faults
and incompatible-source selection were not injected. No backup retention, LSI accuracy,
HAL callback, full-image or Linux HW evidence. Firmware deadlines need SysTick;
external host timeout is independent. F429 CMSIS migration remains pending;
this group does not authorize deleting consumer HAL profiles.
Published-SHA GitHub Docs/full Offline are checked separately before land.

Local regression: Windows docs/host4/4 (98 unittests,8 platform skips), Linux Docker format/host and12 MCU/GCC combinations14/14 PASS. Logs: build/f401-cmsis-rtc-sleep/linux-source/build/ci; Windows: windows-docs-host.json/windows-host.log alongside.
