# C++ context: reproducible example

[Русский](README.md) · [TECH-019](../../docs/en/TESTING_TECHNIQUES.md#tech-019)

Separate computational firmware: Converter::apply(int/float), this, GDB Value casts, object fields
and leaving scope. No peripheral initialization, RTTI/exceptions/LTO; soft-float throughout.
Requires CMake≥3.25, Ninja, Python≥3.11 and GNU Arm GCC/G++ with GDB-Python.

From repository root, substitute tool/stand paths:

```sh
cmake -S tests/cpp-context -B tests/cpp-context/build/f030-og -G Ninja -DCMAKE_TOOLCHAIN_FILE=../firmware/cmake/arm-gcc.cmake -DARM_TOOLCHAIN_ROOT=/path/to/toolchain -DCI_PROFILE=f030r8 -DOPT=Og -DSTM32_GDBTEST_GDB=/path/to/arm-none-eabi-gdb-py3
cmake --build tests/cpp-context/build/f030-og
python -m stm32_gdbtest run --session tests/cpp-context/build/f030-og/hwtest/session.json --test HW_CPP_CONTEXT --prepare-only
python -m stm32_gdbtest run --session tests/cpp-context/build/f030-og/hwtest/session.json --test HW_CPP_CONTEXT --stand /path/to/stand.local.toml
```

Last command connects to MCU and may replace firmware. Preserve original ELF/session and agree recovery
before execution. Afterwards run original CI session's HW_CI_BOOT/HW_CI_GPIO on the same stand.
reset_run alone does not restore a previous Flash image.

CI_PROFILE: f030r8, f103c8, f401cc, f411ce, f429zi, at32f403a; OPT: Og/O2. Use separate build directories
inside tests/cpp-context. Profiles/linker scripts come from sibling tests/firmware. No STM32Cube/Artery
SDK is needed for this computational firmware.

Scenario: [test_cpp_context.py](profile/tests/board/test_cpp_context.py). Enable [capture](../../docs/en/RESULTS.md)
in a separate session.toml to save records. Out-of-scope input differs from optimized_out, which may not
occur even at O2. The scenario checks unquoted int and GDB single-quoted float reach (fixed in Unreleased). GDB objects
belong to their execution context; records hold plain snapshots. [Verified scope](../../docs/en/API_ACCEPTANCE.md).
