# F103 CMSIS: clocks, GPIO, SysTick and TIM2

[Documentation](index.md) · [Русский](../ru/F103_CMSIS_BASELINE.md)

2026-10-01, codex/f103-cmsis-baseline based on a0d6547 (rc.2).
The branch working tree was tested; its base SHA is not claimed as the new code SHA.
WeAct BluePill-Plus STM32F103C8T6, J-Link/SWD, Windows, GCC 13.3.1-1.1,
GDB 14.2.90, J-Link GDB Server 8.32. No UART or external wiring required.

## Implementation and scenarios

One group covers clocks/SysTick, GPIO/blink, TIM2 and IRQs. HSI 8 MHz,
AHB/APB1/APB2 /1, 1 ms SysTick, PB2 initially Low, toggling every 500 ms.
TIM2: PSC=7999, ARR=99, nominal 100 ms. UG loads PSC; UIF is cleared before
IRQ enable. The handler clears UIF without read-modify-write and publishes an event.
Counters are application state; there are no test hooks.

| Scenario | Evidence |
| --- | --- |
| HW_CI_BOOT | .data/BSS and app_loop progress |
| HW_CI_GPIO | APB2 clock, PB2 push-pull 2 MHz, initial Low |
| HW_CI_CLOCK | HSI ready/source, divisors, SystemCoreClock, SysTick LOAD/CTRL |
| HW_CI_BLINK | PB2 alternation, at least 500 firmware ticks between toggles |
| HW_CI_TIM2_INIT | PSC/ARR/SMCR/CR1/DIER, NVIC IRQ 28 and vector 44 |
| HW_CI_TIM2_IRQ | Natural exception 44/UIF, two counter increments, thread progress |
| HW_CI_SYSTICK_IRQ | Natural exception 15, vector 15, tick increment, thread progress |

[TECH-001/002](TESTING_TECHNIQUES.md): physical expectations independent of CMSIS
expressions; evaluate macros in board.c, where the device header is included.
F1 GPIO uses APB2/CRL, not F0/F4 AHB/MODER. CEN is checked after timer startup,
not before HAL setup. HAL callbacks/handles/force_return are outside this group
and remain in the HAL regression.

## Hardware evidence

**7/7 PASS**, then original consumer HAL firmware restored:
HW_BOOT/HW_BLINK PASS, teardown reset_run. MCU left running.
ELF SHA256: `29d83ac6a6e67276d713776a27fb2992ec1fa6f60639555491452a1e48d05ba7`.
Local evidence: build/f103-cmsis-baseline/
f103-windows-full-20261001T074519Z/summary.json; JSON/JUnit:
tests/firmware/build/f103c8/hwtest/runs. Summary links individual reports.

First run 074453: BOOT PASS, GPIO ERROR — the scenario retained another family's
RCC_AHBENR_GPIOBEN name. HAL was restored and checked even after the error.
Corrected the expression to RCC APB2/IOPBEN, firmware unchanged; the full rerun
is recorded above. The contract checked the correct names, not the unlisted
incorrect expression: successful prepare does not prove the entire scenario correct.

## Limits and reproduction

GDB stops affect timing; IRQ pending/UIF may coalesce events. These checks do not
prove HSI accuracy, jitter, absence of lost events or visible LED light.
External vectors are defined only through TIM2 (IRQ 28); extend startup before
enabling later IRQs. The delay uses WFI, but separate Sleep/residency checks are
outside this group. ADC/DMA and RTC are subsequent groups.

From tests/firmware: cmake --preset f103c8, cmake --build --preset f103c8,
ctest --preset f103c8-offline. Then use the standard CLI from the module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f103c8/hwtest/session.json --test <ID> --stand <local.toml>`.
Select BluePill/J-Link and prepare the consumer restore-session before hardware runs.
run_hw.py checks the boot/GPIO lifecycle, not all seven scenarios.

Offline: Windows F103 CTest 8/8 (seven prepare + traceability), host98
(8 platform skips). Linux Docker: host and F030/F103/F411 × GCC13/14/15,
10/10 stages PASS, including negative contracts and image policy.
Evidence: build/f103-cmsis-baseline/linux-source/build/ci/summary.json.
Other boards were not hardware-tested in this group.
