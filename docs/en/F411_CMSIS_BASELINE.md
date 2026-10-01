# F411 CMSIS: clocks, GPIO, SysTick and TIM2

[Documentation](index.md) · [Русский](../ru/F411_CMSIS_BASELINE.md)

2026-10-01, working tree codex/f411-cmsis-baseline based on main d97903c.
WeAct BlackPill F411CE + ST-Link/SWD, OpenOCD 0.12.0, Windows,
GCC 13.3.1-1.1/GDB 14.2.90. No UART or external wiring.
The base SHA does not identify modified sources. API/schemas and rc.2 version are unchanged.

## Implementation and checks

Configuration reference: [RM0383](https://www.st.com/resource/en/reference_manual/dm00119316-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf), RCC/GPIO/TIM2.

HSI16 MHz supplies SYSCLK/AHB/APB1/APB2 without dividers; PLL is disabled after switching.
SystemCoreClock=16000000, SysTick LOAD=15999; its ISR increments board_ticks_ms.
LED interval is500 firmware ms through board_delay_ms/WFI instead of a busy loop.
PC13 is push-pull, low speed, no pull; initial High means LED off.
F103 uses active-high PB2 and HSI8 MHz, so its numerical expectations cannot be copied.

TIM2 receives APB1 16 MHz, PSC=15999, ARR=99: nominal100 ms.
UIF is discarded after UG; IRQ28/vector44 publishes board_timer_events.
UIF is cleared with rc_w0, not read-modify-write. Startup includes SysTick/TIM2 vectors.

| HW_CI_* | Evidence |
| --- | --- |
| BOOT | .data delay=500, BSS counters=0 at main, app_loop progress |
| GPIO | PC13 clock, mode/type/speed/pull and initial High |
| CLOCK | HSI/SWS, dividers, SystemCoreClock, SysTick LOAD/CTRL |
| BLINK | PC13 alternates after ≥500 firmware ticks |
| TIM2_INIT | Clock, PSC/ARR, DIER/CR1/SMCR, NVIC and vector44 |
| TIM2_IRQ | Natural exception44 with UIF, event++ and thread resumption |
| SYSTICK_IRQ | Natural exception15, tick++ and thread resumption |

-g3 contracts check CMSIS macros in board.c; exception identity uses SCB ICSR,
not an assumed xPSR register name. See [TECH-001/002/003](TESTING_TECHNIQUES.md).
**7/7 HW PASS**, followed by consumer HAL restoration: HW_BOOT/HW_BLINK PASS,
reset_run. The MCU was left running; no other boards were exercised.

ELF SHA256: `2a5dad68f9832692cde09c993796bb4ce617fb7c851903d1594bba593988d58d`.
Evidence: build/f411-cmsis-baseline/f411-windows-full-20261001T110610Z/summary.json,
linked JSON/JUnit; tested-source-hashes.json records sources. Artifacts are Git-ignored.
Windows prepare/traceability:8/8 PASS.

## Reproduction and limits

Use f411ce and f411ce-offline presets in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f411ce/hwtest/session.json --test <ID> --stand <local.toml>`.
Select F411/OpenOCD explicitly. Restore HAL and check HW_BOOT/HW_BLINK in finally.

Counters and intervals are verified against firmware ticks, not an independent clock.
GDB halt changes timing; GPIO registers do not prove emitted light. The application uses
WFI, but interrupted WFI/Sleep validation is a later group. Oscillator failures, jitter,
lost IRQs and absolute frequency are not covered. Next: ADC/DMA/units/failures,
then RTC/Sleep/recovery. CMSIS registers do not replace HAL callback/return-code
checks; those techniques remain in the guide. GitHub Docs/Offline are checked after
push; the consumer gitlink remains at rc.2.

Local Windows docs/host4/4 (98 unittests, 8 platform skips), C/H format PASS.
Linux Docker host and nine MCU/GCC combinations:10/10 PASS; logs under
build/f411-cmsis-baseline/linux-source/build/ci. These are offline checks, not Linux HW.
