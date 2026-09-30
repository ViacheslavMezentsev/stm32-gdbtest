# HAL macros in scenarios

[Documentation](index.md) → HAL macros · [Русский](../ru/HAL_MACRO_GUIDE.md)

The recommendations come from reviewing the Exported Macros in the adc, gpio, rcc,
tim and uart headers of CubeF4 V1.28.3, checking the corresponding F1 definitions and
experiments on ELF files. Installed libraries are not modified. A definition is taken
from the debug information of the built ELF, not substituted from the current header
with `macro define`.

## Choosing a macro

| Area | Candidates for observation | What to consider |
| --- | --- | --- |
| RCC | `__HAL_RCC_*_IS_CLK_ENABLED()` | A predicate of the current state, not proof that ENABLE was called. Verified for GPIOB/C, ADC1, TIM2, DMA1/2. |
| TIM | `__HAL_TIM_GET_AUTORELOAD`, `GET_COUNTER`, `GET_IT_SOURCE`, `GET_FLAG` | ARR verified on TIM2. CNT changes over time; an IRQ handler may clear SR before the stop. |
| ADC | `__HAL_ADC_GET_FLAG`, `GET_IT_SOURCE` | Align the stop point with EOC/OVR handling; a flag does not prove a correct measurement. Candidate list for now. |
| GPIO | `__HAL_GPIO_EXTI_GET_FLAG`, `GET_IT` | Return a mask, not necessarily 1. MODER/CRL need CMSIS fields; there is no HAL predicate for the pin mode. EXTI is not verified here yet. |
| UART | `__HAL_UART_GET_FLAG`, `GET_IT_SOURCE` | Mind SR/DR sequences: per the header comment `CLEAR_PEFLAG` reads SR and DR, and such reads clear state. UART is not verified on the stands yet. |

`ENABLE`, `DISABLE`, `SET`, `CLEAR`, `RESET_HANDLE_STATE`, EXTI IRQ generation and
similar macros are actions, not observations; only explicitly described
state-changing scenarios may use them. A `GET` name alone does not guarantee
harmlessness: review the expansion, the reference manual, arguments and read side
effects. A statement macro `do { ... } while (0)` is not an ordinary C expression.

## Scenario rules

- Reach a specific function or line first, then evaluate the macro.
- **The context is a function from the compilation unit where the macro is
  defined.** GDB takes macros from the debug information of a specific `.c` file: if
  the device header is included only in `board.c`, a stop in `app_loop` from `app.c`
  does not see `RCC` or `GPIO_*`. The CI firmware follows this: the macro context is
  `board_led_toggle`.
- `Target.value()` uses `gdb.parse_and_eval`. For a mask result compare the mask or
  normalize it with bool; do not equate any mask with 1.
- A separate `t.check` per condition keeps diagnostics clear.
- Prefer CMSIS `_Msk`/`_Pos` over unexplained shifts and masks; the expected mode
  and divider values are set independently by the profile.
- Do not replace a physical expectation with an arbitrary HAL constant: on F411
  `ADC_CHANNEL_TEMPSENSOR` carries a service flag, while the rank must contain 18.
- Do not claim peripheral coverage from a clock-enable check: start, IRQ/DMA, data,
  errors and observed effects in the application are needed.

## Offline contract

In the profile's `Tests/contracts.json` (schema 1) a macro contract looks like this:

```json
{
  "macros": {
    "context": "loop",
    "expressions": ["__HAL_RCC_ADC1_IS_CLK_ENABLED()", "RCC_CFGR_HPRE_Msk"]
  }
}
```

The contract name goes into `@case(..., contracts=("clock_macros",))`. Before the
server the runner starts a separate GDB without connecting to the MCU: it finds the
`context` function in the ELF, selects its source position with `list *address`,
checks `info macro` and runs `macro expand`. The report keeps the context, expression
and expansion. Nothing is evaluated with `parse_and_eval`, no registers are read, no
functions are called. A missing definition or expansion is ERROR before the server
starts. The context is mandatory; inheriting the context of a previous contract is
not allowed.

This checks presence and expansion; it is **not** proof of the absence of side
effects, full HAL compatibility or correct run-time arguments and types. The full C
grammar is not checked: names and simple calls with identifiers, numbers, `&`, `*`,
commas and spaces are allowed. Arbitrary GDB commands in declarations are rejected.
An unknown nested identifier and the correctness of the final expression may need
additional contracts and hardware checks. The exact macro body is not pinned as a
reference: a changed expansion is visible in the report but not rejected by itself.

## Applicability of the examples

The table contains verified F1/F4 examples and separately marked candidates; it is
not a promise that the macros exist for every STM32 and HAL. Real contracts and
hardware results are [in the stand project](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/HAL_MACRO_GUIDE.md) (Russian).

[Techniques catalogue TECH-001…008](TESTING_TECHNIQUES.md) — stable scenario references, build prerequisites, limits and restoration. Preserve TECH-001/003/004 references when migrating HAL scenarios.
