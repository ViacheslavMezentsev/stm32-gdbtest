# API, CLI and migration

[Documentation](index.md) → API · [Русский](../ru/API.md)

Status: release candidate **0.1.0-rc.1** (Python `0.1.0rc1`), `API_VERSION = 1`. This numbers the
described API surface; it is not a 1.0 stability promise and not a GDB version. The
module is delivered as a Git submodule; pip installation is not supported yet, and
the name still has to be checked for uniqueness before publishing. Requirements:
the [specification](../TECHNICAL_SPECIFICATION.md) (Russian).

## Integration from the source tree

```cmake
include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    MANIFEST_INPUTS "${CMAKE_CURRENT_SOURCE_DIR}/profile/firmware_FLASH.ld")
```

- `STM32_GDBTEST_SOURCE_DIR` is the checkout root containing the `stm32_gdbtest`
  package; in the consumer example it is a cache PATH.
- The project must enable CTest (`include(CTest)` or `enable_testing()`) and create
  the firmware target before `stm32_gdbtest_attach`.
- One firmware target of the top-level CMake directory, the Ninja generator and a
  build directory inside `PROJECT_SOURCE_DIR` are supported. Build, build manifest
  preparation and hardware runs work on Windows and Linux ([Linux stand](LINUX_STAND.md)).
- `PROFILE_DIR`, `PROFILE` and `MANIFEST_INPUTS` paths are absolute. `PROFILE_DIR`
  contains `Tests/board/test_*.py`, `Tests/requirements.md`, `Tests/contracts.json`
  when contracts are used, and `target.toml`. The scenario directory may also be named
  `tests`.
- `PROFILE` is the MCU description as a separate file instead of
  `PROFILE_DIR/target.toml`. Several MCU variants of one firmware then share scenarios,
  requirements and contracts; each variant is its own build with its own `PROFILE`:

  ```cmake
  stm32_gdbtest_attach(firmware_target
      PROFILE_DIR "${PROJECT_SOURCE_DIR}/hil"                    # shared Tests/
      PROFILE "${PROJECT_SOURCE_DIR}/hil/profiles/${MCU}.toml")  # G474.toml, G431.toml
  ```
- `MANIFEST_INPUTS` adds files to the manifest snapshot and to relink dependencies.
- `SELF_TESTS` enables the module's own host tests (`host.hwtest`); consumers do not need it.
- stm32-cmake-yml is not an API dependency.

CMake creates tests: `hw.<ID>` (hardware, labels `hw` and the scenario labels,
`RESOURCE_LOCK stm32_swd`), `prepare.<ID>` (preparation without hardware, labels
`host` and `prepare`) and `host.traceability`. The `check-hw` target runs the whole
CTest with a JUnit report.

The cache variable `STM32_GDBTEST_GDB` selects GDB with Python and
`STM32_GDBTEST_STAND` the local stand TOML. Other CMake variables with this prefix
are internal. Generated `session.json`, `tests.cmake` and `build-manifest.json` are
not edited by hand. `stm32_gdbtest_register` is internal.

## Python scenarios

```python
from stm32_gdbtest import case

@case("HW_GPIO", timeout_s=20, labels=("gpio",), contracts=("gpio_macros",))
def gpio(t):
    t.reach("loop")
    t.check("GPIOC clock", t.value("__HAL_RCC_GPIOC_IS_CLK_ENABLED()"), 1)
```

The example needs firmware with a `loop` function and a declared `gpio_macros`
contract; it is not a universal test for any STM32.

- The decorator imports in plain Python without the `gdb` module. Collection does
  not execute test code: ID, timeout, labels and contracts are read from the AST and
  must be literals.
- ID — `HW_[A-Z0-9_]+`; `timeout_s` — integer 1…300 s (default 20); labels —
  `[a-z0-9_-]+`; contract names — `[a-z][a-z0-9_]+`.
- The decorator is named `case` without an alias. A test is a top-level function with
  one Target parameter; the agent calls it after reset and a stop in `main`.
- Project helpers are importable from the consumer root. No test hooks are added to
  the firmware.

Public operations of the Target passed to the scenario (the `target` module is
imported only inside GDB):

| Operation | Contract |
| --- | --- |
| `check(name, actual, expected)` | Records the result; a mismatch raises `CheckFailed` → FAIL |
| `value(expression)` | `gdb.parse_and_eval`, refuses optimized-out values, returns `int` |
| `fields(expression, expected)` | Per-field comparison of scalar fields with an `int` or a C expression |
| `reach(function, when=None)` | Temporary hardware breakpoint, `continue`, checks stop reason, frame and condition; the frame name is compared without `[clone …]` and parameters (LTO clones) |
| `breakpoint(function, temporary=False, when=None)` | Hardware breakpoint with pending and profile budget checks |
| `set_value(expression, value)` | Explicit write with a before/after log; the author checks that an MMIO write is safe |
| `force_return(expression)` | Forced return from the current frame with a log; the function body is skipped |
| `clear()` | Deletes the Target's breakpoints, including those on fault handlers |

`boot`, `close`, `on_stop`, `report`, `owned`, `stops` and Target creation are the
agent's internal lifecycle. GDB calls are allowed only on its main thread. `-g3`
keeps macros but not unused functions and symbols; see [HAL macros](HAL_MACRO_GUIDE.md)
and [contracts](CONTRACTS.md).

## CLI

From the module checkout root (from another directory use the absolute path of
`stm32_gdbtest/cli.py`):

```powershell
python -B -m stm32_gdbtest --version
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/Tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/Tests/board --requirements examples/minimal-consumer/profile/Tests/requirements.md
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --prepare-only
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --stand path/to/stand.local.toml
python -B -m stm32_gdbtest doctor --stand path/to/stand.local.toml
```

The logical CLI name is `stm32-gdbtest`; a separate executable will come with packaging.

| `run` option | Purpose |
| --- | --- |
| `--session` or `--package`, `--test` | Generated `session.json` or a prepared run package, and scenario ID |
| `--gdb`, `--workdir` | For `--package`: the stand's GDB (otherwise looked up like `doctor`) and the extraction directory (default `build/ddtt-packages`) |
| `--stand` | Local stand; selection order: `--stand` → `STM32_GDBTEST_STAND` → `session.stand`; with a `[remote]` table the server starts on the stand host over SSH, the report has `server_host`, the SSH log is `tunnel.log` |
| `--timeout` | External GDB deadline, 0 < t ≤ 300 s; defaults to the scenario's `timeout_s` |
| `--identity-policy warn\|strict` | DEV_ID policy; order: CLI → `STM32_GDBTEST_IDENTITY_POLICY` → `warn` |
| `--image-policy` | Full-image policy; alternative — an absolute `STM32_GDBTEST_IMAGE_POLICY` |
| `--prepare-only` | Only the steps before the GDB server, no hardware |

`--prepare-only` runs every step before the GDB server: stand (if selected),
profile, ELF snapshot, build manifest, requested contracts, sections and image,
including full mode. The debugger lock, server and connection are not used; the
report gets `mode: prepare` and `hardware_accessed: false`. A stand is optional in
this mode; if one is selected, it is validated completely, including the J-Link mapping.

`doctor [--gdb PATH] [--stand TOML] [--json]` checks the environment without accessing
the debugger: host Python, GDB-Python ≥ 3.11 and binutils next to it, CMake and Ninja,
the lock directory, the stand (for OpenOCD — that `interface/stlink.cfg` exists) and on
Linux ST-Link and J-Link devices on USB with access rights. The output is OK/WARN/FAIL
lines (`--json` gives a list of `{name, status, detail}`); the exit code is 1 on FAIL. GDB
is looked up as `--gdb` → `STM32_GDBTEST_GDB` → `arm-none-eabi-gdb-py3`/`arm-none-eabi-gdb`
on `PATH` → `bin` under `ARM_TOOLCHAIN_ROOT` → on Windows the default xPack directory in the
user profile. For a stand with `[remote]` the local OpenOCD and USB checks are replaced by
checks of the stand host over SSH (`remote`, `remote-server`, `remote-lock`, `remote-usb`,
40 s limit).

`pack --session S --output P.zip [--test ID …] [--include PATH …]` prepares scenarios without
hardware and writes a prepared run package; `run --package` checks the SHA-256 of every
package file and adds a `package` field to the report ([hardware CI](HARDWARE_CI.md)).

`collect --cmake/--workspace` is the CMake generation interface and is rarely used by hand.

`run` exit codes: PASS — 0, FAIL — 1, ERROR — 2; argument errors also give 2. A
failure before the run directory exists does not guarantee JSON/JUnit. An expected
failure stays ERROR and never turns into PASS.

Stable schemas: target 1, contract registry 1, build manifest 1, runtime
compatibility 1, image policy 1, prepared run package 1. `session.json` is an internal artifact without a
stable schema promise. Direct calls into `runner`, `contracts`, `processes` are an
internal development API; consumers use CMake, the CLI and the Target operations.
Details: [getting started](GETTING_STARTED.md), [manifest](MANIFESTS.md),
[identity](TARGET_IDENTITY.md), [GDB servers](BACKENDS.md),
[debugger ownership](DEBUGGER_OWNERSHIP.md). On Linux `STM32_GDBTEST_LOCK_DIR` sets the
base directory of the locks: by default the system temporary directory (`/tmp` or
`TMPDIR`), with `stm32-gdbtest-locks` inside.

## Image verification

By default Flash is compared by the loadable ELF sections (LMA); gaps are not
checked. The BIN is built from these sections only, with gaps filled with 0xFF. GNU
`arm-none-eabi-objdump` and `arm-none-eabi-objcopy` must sit next to GDB. This is
not a CRC check of the whole region.

Full image: `run --image-policy file.toml` or `STM32_GDBTEST_IMAGE_POLICY` (the CLI
wins) selects an `[image]` schema 1 range. The canonical BIN, transport ELF,
CRC-32/ISO-HDLC over the readback, report fields and limits are described in
[images and CRC](IMAGES.md). The mode adds no code or CRC field to the firmware; the
CRC is computed on the host, not by the MCU peripheral.

## Migrating from hwtest

| Before | Now |
| --- | --- |
| `from hwtest import case` | `from stm32_gdbtest import case` |
| `hwtest/cli.py` | `stm32_gdbtest/cli.py` or `python -m stm32_gdbtest` |
| `hwtest/cmake/HwTest.cmake` | `stm32_gdbtest/cmake/STM32GDBTest.cmake` |
| `hwtest_attach` | `stm32_gdbtest_attach` |
| `HWTEST_SOURCE_DIR` / `HWTEST_GDB` / `HWTEST_STAND` | `STM32_GDBTEST_SOURCE_DIR` / `STM32_GDBTEST_GDB` / `STM32_GDBTEST_STAND` |
| `HWTEST_IDENTITY_POLICY` | `STM32_GDBTEST_IDENTITY_POLICY` |

Old import, CLI and CMake aliases are not provided. The environment variables
`HWTEST_STAND` and `HWTEST_IDENTITY_POLICY` make the runner fail explicitly, so an
outdated stand selection is never silently ignored. The internal `RUN` and
`CONTRACT_REQUEST` variables also use the new prefix; the host sets them.

Migration steps: update imports, local presets and commands, move custom cache
values to the new names, remove the old environment variables and run configure and
build again. An old CTest without configure still contains the previous package
paths. Preset names, `check-hw`, `host.hwtest`, the `hwtest` report directories,
`HW_*` IDs, TOML/JSON formats and the lock namespace are kept. The migration needs
no firmware test hooks and does not imply support for an arbitrary STM32, operating
systems other than Windows and Linux for hardware runs or automatic cleanup of
processes after a host crash.

F030 CMSIS fixture: the core API is unchanged. `app_delay` now specifies SysTick milliseconds (500); `app_state.ticks` remains a loop counter. See the four scenarios in the [baseline report](F030_CMSIS_BASELINE.md).

Core API unchanged. board_timer_events is F030 fixture state, not public API. [TIM3/IRQ](F030_CMSIS_TIMER.md).

F030 ADC/DMA: raw samples and timeout, core API unchanged. [ADC/DMA](F030_CMSIS_ADC_DMA.md).
