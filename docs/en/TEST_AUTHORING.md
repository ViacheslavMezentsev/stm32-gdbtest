# Writing tests by people and AI agents

[Documentation](index.md) → Writing tests · [Русский](../ru/TEST_AUTHORING.md)

The process is the same for manual work and agent generation. A person needs only a
Python editor or VS Code and the commands below; an agent is not a dependency.

For an agent this is a closed loop: it writes the requirement, puts a scenario into the
repository, checks it without hardware (`run --prepare-only`), runs it on a stand and
reads `result.json`. The result is not an answer in a chat but a test case of the
project that later runs again manually, in CI or on a stand in a loop. An agent does
not change the stand, the debugger firmware or dangerous Flash settings without the
owner's agreement ([maintenance](maintenance.md#working-with-hardware)).

1. Write the observable requirement and its ID in `tests/requirements.md`. Define the
   acceptable effect of halt/reset and the failure criterion.
2. Prepare `target.toml` for the specific MCU, board and firmware: Flash, identity,
   breakpoint budget, fault handlers. Build Debug with `-g3`, check the ELF and manifest.
3. Write a top-level function in `profile/tests/board/test_*.py`. The module is not
   changed for a project scenario; helpers live in the project.
4. When HAL or CMSIS macros are used, choose pure getter and predicate expressions
   and a context — a function from the compilation unit where the macro is defined;
   add `contracts.json`. Do not present a setter as a read; mind read-to-clear, W1C,
   FIFO and SR/DR sequences ([HAL macros](HAL_MACRO_GUIDE.md)).
5. Without a board: collection and traceability, then `run --prepare-only` — it runs
   the offline contract, manifest and image checks before the GDB server.
6. Name the exact stand, run one test, study JSON, JUnit and GDB logs; only then
   extend the set. Record the restored state.

The consumer example already has an `app_loop` function and CMSIS macros in the ELF;
`profile/tests/board/test_blink.py`:

```python
from stm32_gdbtest import case

@case("HW_CONSUMER_GPIO", labels=("gpio",), contracts=("consumer_gpio",))
def gpio(t):
    t.reach("app_loop")
    t.check("GPIOC clock", t.value("(RCC->AHB1ENR & RCC_AHB1ENR_GPIOCEN) != 0"), 1)
```

Three more examples for Cortex-M0, M3 and M4 are the CI firmware profiles
`tests/firmware/profiles/*`.

From the module root, with the consumer paths:

```powershell
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/tests/board --requirements examples/minimal-consumer/profile/tests/requirements.md
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --prepare-only
```

After building and agreeing on an F411/ST-Link/SWD stand, the hardware command
(programs Flash if the image differs; never substitute another board's profile):

```powershell
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --stand path/to/stand.local.toml
```

`check` records the result and gives FAIL on a mismatch. `value` returns an `int` from
a GDB expression; an unknown macro or symbol gives ERROR, not zero. `reach` checks the
actual stop reason: a breakpoint that was set successfully is not a test by itself. A
GPIO register value does not prove the pin voltage, `uwTick` does not measure an exact
external duration, Sleep under SWD does not prove current consumption.

**LTO.** With `-flto` functions from different files are inlined into each other: the code
of an inlined function may run out of source order (`reach` steps wait for a function that
has already run until the timeout), `force_return` from an inlined function is impossible,
and GDB may name the frame by a clone (`Func() [clone .constprop.0]`; `reach` accepts such
names). For scenarios that walk through calls or replace a return value, build a test
variant without LTO: add `-fno-lto` after `-flto` in the compile and link options (GCC uses
the last one). The checked firmware is then the variant without LTO.

**Several MCU variants.** When one firmware builds for different MCUs with the same logic,
keep scenarios and requirements in one `PROFILE_DIR/Tests` and each MCU description as a
separate file selected with `PROFILE` ([API](API.md)); each variant is its own build.

A task for an agent must state the MCU, firmware or ELF, stand, goal and allowed
actions. Do not guess the hardware wiring and do not set expectations from an observed
result just to get a PASS; a person checks the same assumptions. Negative scenarios
keep the ERROR or FAIL reason; exceptions are not suppressed.

External instruments and power are a deferred host-controller interface
([roadmap](../../TODO.md), Russian). There is no standard power-cycle and reconnect API
yet; do not emulate it with hidden calls from a background GDB thread.

[Techniques catalogue TECH-001…008](TESTING_TECHNIQUES.md) — stable scenario references, build prerequisites, limits and restoration. Preserve TECH-001/003/004 references when migrating HAL scenarios.
