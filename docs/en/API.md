# API, CLI and migration

[Documentation](index.md) → API · [Русский](../ru/API.md)

[Release v0.3.0](../releases/v0.3.0.md): stm32-gdbtest 0.3.0; candidate v0.2.0-rc.1 was never published. Historical evidence follows.

The v0.4.0 candidate has package version 0.4.0 and `API_VERSION=2`:
`value`, `fields`, `set_value`, `force_return` have been removed. The release is
unpublished; final-SHA acceptance remains.
See the [reference and migration](api/index.md).
Schema 2 selects reset commands from the backend section of `target.toml`; `api.reset.command`
does not affect execution. Read the effective command from `t.profile.stand["reset_command"]`.
Schema 1 keys apply only to OpenOCD; the reset override does not change host recovery.

Production first-package examples and five-MCU verification: [accepted results](API_ACCEPTANCE.md).

[Methods and properties reference](api/index.md) — individual cards, examples and support versions.

## 0.3.0 package: numbers, migration and aliases

The 0.4.0 candidate fixes `evaluate(path, as_type=str)` for a `char[]` whose GDB size is zero
from its address up to NUL or `STRING_LIMIT = 256`, like a pointer. The `const char *` cast workaround
is no longer required. Known `char[N]` bounds remain enforced; an unsized array without an address
raises `ApiError(read_failed)`. The method signature is unchanged; `API_VERSION=2`
reflects removal of former methods. API specification 0.3.11, §4.18.

Public method cards live in the [reference](api/index.md), grouped into methods, properties,
decorators, classes and errors. The contract is fixed by API specification 0.3.0-rc.1; the module
implements every listed method and is verified on five stands. The numbers agreed on 2026-10-04 and
the transition from the former names are recorded below.

| `api.toml` parameter | Default | Maximum | Where it applies |
| --- | ---: | ---: | --- |
| `frames.limit` | 16 | 64 | the frame walk of `frames()` |
| `call.depth` | 1 | 2 | the call depth of `call()` |
| `call.args_max` | 4 | 8 | the argument count of `call()` |
| `execute.output_limit_chars` | 2048 | 16384 | the journal output length of `execute()` |
| `measurements.series_length` | 5 | 20 | the series length of a measurement scenario |
| `reset.command` | from the backend | — | the `reset()` command |
| `app.delay_ms` | from the firmware | — | the application interval of the fixture firmware: the
  waits between checks follow it |

The values are read from `api.toml`; a method call may lower `limit` and a profile may raise it up to
the maximum. The reset command comes from the backend dialect: OpenOCD uses `monitor reset halt`
and `monitor reset run`, ST-LINK GDB Server and J-Link use `monitor reset`; the section of the target
profile for the selected server (`[openocd]`, `[jlink]`, `[stlink]`) or a session may override it.
The `api.toml` key `reset.command` is removed. The journal limits, `breakpoint_limit=4`
and `timeout_s=20` stay as in the effective tables.

Transition from former names: in release 0.3.0 these four methods warn with
`deprecated`; they are removed in the 0.4.0 candidate.

| Former name | New name | Note |
| --- | --- | --- |
| `value(expression)` | `read(path)` or `evaluate(expression)` | read an object by path or evaluate a GDB expression; check the result type |
| `fields(expression, expected)` | `check([(name, path, expected), …])` | the table evaluates string expectations |
| `set_value(expression, value)` | `write(path, value)` | the applied value gains verification |
| `force_return(expression)` | `ret(value=None)` | the return becomes an operation with a result |
| `config` / `config_props` | `profile` (sections, `get`, `origin`) | removed in 0.3.0 without an alias; [profile](api/profile.md) |
| `check_range`, `check_near`, `check_in`, `check_table`, `write_memory`, `to_dict` | `check` with `within`/`near`/`one_of`, `check(rows)`, `memory(address, data)`, `snapshot()` | candidate 0.3.0 names replaced before the release |
| `case(...)` | `test(...)` | no warning: `@case` stays the primary name, `@test` is an alias |
| `RecordError` | an `ApiError` subclass | the public import is preserved |

## First package: records and configuration

Release 0.3.0; `API_VERSION=1`, api.toml schema=1. [API spec](../TECHNICAL_SPECIFICATION_API.md), [accepted results](API_ACCEPTANCE.md).

`record(name, data)` appends a deep copy and returns None. `records(name=None)` returns detached mutable copies: `{'sequence': 1, 'name': 'adc', 'data': ...}`. Names may repeat. The filter is an exact nonempty str; None selects all. Insertion order and sequence starting at 1 survive filtering.

Data accepts exact built-in None/bool/int, finite float, valid Unicode str, list and dict with string keys. Subclasses, tuple, bytes, GDB objects, cycles and NaN/Inf are rejected. Shared acyclic references are copied independently. Failures consume neither budget nor sequence. Each scenario invocation owns its journal, retained across clear/reset/continue; there is no automatic export, MCU read or change to check outcomes.

```python
from statistics import mean, stdev
from stm32_gdbtest import RecordError

# At each agreed stop:
t.record('adc', {'vdda_mv': t.read('board_measurement.vdda_mv')})
# After at least two measurements:
values = [r['data']['vdda_mv'] for r in t.records('adc')]
result = {'mean_mv': mean(values), 'sample_stdev_mv': stdev(values)}
```

Slices, filters and any/all use ordinary Python. RecordError(ValueError) imports without GDB. Codes: invalid_name/unsupported_type/invalid_text/non_finite/cycle/limit_exceeded. For limit_exceeded, limit is records/nodes/depth/text_bytes/integer_bits. Message text and precedence of simultaneous violations are unspecified. Uncaught errors produce ERROR; check still produces FAIL. MemoryError is not disguised.

| records | Default | Maximum |
|---|---:|---:|
| max_records | 128 | 1024 |
| max_nodes | 4096 | 32768 |
| max_text_bytes | 65536 | 524288 |
| max_depth | 8 | 32 |
| max_integer_bits | 256 | 1024 |

Values are integers from 1 through the maximum, excluding bool. Records/nodes/bytes limit the whole journal; data depth starts at 0, integer_bits uses int.bit_length. Nodes count names, keys, values and containers; UTF-8 bytes count names, keys and strings. The envelope is excluded. These are not RSS or retained-copy limits.

### Explicit configuration and migration

```cmake
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${PROJECT_SOURCE_DIR}/hil"
    SESSION_CONFIG "${PROJECT_SOURCE_DIR}/hil/session.toml")
```

```toml
# session.toml: relative references resolve from its directory
[config]
target = "target.toml"
api = "api.toml"
image = "full_image.toml" # optional
```

```toml
# api.toml
schema = 1
[records]
max_records = 256
[user.measurement]
count = 10
```

`t.profile.get('user.measurement.count')` reads a scenario parameter. `profile` sections: target/api/user/image with core defaults; an absent image is None, a selected one is the policy itself. `profile.files` holds the source-byte sha256 and reference of captured files, `profile.origin(path)` the source of a value (file, default, environment override or the run). Sections and nested containers are immutable; arrays become tuples. TOML dates/times and unknown fields survive. reference does not guarantee source-path availability on another host.

SESSION_CONFIG conflicts with PROFILE, --image-policy and STM32_GDBTEST_IMAGE_POLICY. PROFILE_DIR still selects scenarios. target is required; omitted api selects defaults, image selects ELF sections. An explicitly selected missing/invalid file produces ERROR before MCU access. Unknown api fields survive; target/image schemas stay strict.

CLI --session accepts the existing generated ELF/GDB/tests JSON with an added session_config reference. profile derives from TOML; repeat CMake configure/build after changing target. Without SESSION_CONFIG there is no discovery: old calls work, config_props describes actual legacy sources and api uses defaults.

New pack captures TOML in an internal capsule (base64/SHA256/defaults fingerprint); runner/GDB validate it without original files. New packages require tools supporting the extension; do not use older tools. Old packages use legacy mode. Prepare a new package to change its captured configuration. This is not a record/records export format.

Status: **0.3.0** is published (stm32-gdbtest `0.3.0`, [notes](../releases/v0.3.0.md));
the release branch prepares **0.4.0** (`API_VERSION=2`). This numbers the API
surface; it is neither a 1.0 stability promise nor a GDB version. The
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
  contains `tests/board/test_*.py`, `tests/requirements.md`, `tests/contracts.json`
  when contracts are used, and `target.toml`. Use `tests` for new projects; legacy `Tests` remains supported.
- `PROFILE` is the MCU description as a separate file instead of
  `PROFILE_DIR/target.toml`. Several MCU variants of one firmware then share scenarios,
  requirements and contracts; each variant is its own build with its own `PROFILE`:

  ```cmake
  stm32_gdbtest_attach(firmware_target
      PROFILE_DIR "${PROJECT_SOURCE_DIR}/hil"                    # shared tests/
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
    t.check("GPIOC clock", t.evaluate("__HAL_RCC_GPIOC_IS_CLK_ENABLED()"), 1)
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
| [`check(name, actual, expected)`](api/check.md) | Records the result; a mismatch raises `CheckFailed` → FAIL |
| [`read(path)`](api/read.md) / [`evaluate(expression)`](api/evaluate.md) | Typed object read / GDB/C expression evaluation |
| [`reach(location, condition=None)`](api/reach.md) | Temporary hardware breakpoint, `continue`, checks stop reason, frame and condition (`when=` is the former name of `condition`); the frame name is compared without `[clone …]` and parameters (LTO clones) |
| [`breakpoint(location, temporary=False, *, condition=None)`](api/breakpoint.md) | Hardware breakpoint (`Point`) with pending and profile budget checks; `when=` is the former name of `condition` |
| [`write(path, value)`](api/write.md) | Explicit verified write with a before/after log; the author checks that an MMIO write is safe |
| [`ret(value=None)`](api/ret.md) | Forced return from the current frame with a result and log; the function body is skipped |
| [`clear()`](api/clear.md) | Deletes the Target's breakpoints, including those on fault handlers |

`boot`, `close`, `on_stop`, `report`, `owned`, `stops` and Target creation are the
agent's internal lifecycle. GDB calls are allowed only on its main thread. `-g3`
keeps macros but not unused functions and symbols; see [HAL macros](HAL_MACRO_GUIDE.md)
and [contracts](CONTRACTS.md).

## CLI

From the module checkout root (from another directory use the absolute path of
`stm32_gdbtest/cli.py`):

```powershell
python -B -m stm32_gdbtest --version
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/tests/board --requirements examples/minimal-consumer/profile/tests/requirements.md
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

F030 ADC conversion and numeric scenarios; core API unchanged. [ADC units](F030_CMSIS_ADC_UNITS.md).

F030 Sleep/WFI: profile scenarios using GDB unwind; core API unchanged. [Sleep evidence](F030_CMSIS_SLEEP.md).

F030 RTC: LSI Alarm A, 16/16 HW PASS, HAL restored. Core API unchanged. [RTC](F030_CMSIS_RTC.md).

F030 busy ADC check; API unchanged. [Report](F030_ADC_BUSY.md).

F030 RTC deadline through argument injection; API unchanged. [Report](F030_RTC_DEADLINE.md).

Owned profiles/examples and new packages use `tests`; old `Tests` inputs remain supported. Local remote stands use ignored `<profile>-<backend>.remote.toml` (`openocd`, `jlink`, `stlink`). Reconfigure after renaming. [Conventions](maintenance.md).

[Standalone F030 HAL regression](F030_HAL_REGRESSION.md): test consumer, no API changes.

[CI hal level](testing.md) validates the fixture; public APIs/schemas are unchanged.

## Package evidence retention (rc.2)

Repeated run --package extracts inputs into a new
`<workdir>/<16 SHA-256 characters>/sessions/session-*`. Reports from each invocation
remain in its `<workdir>/<16 SHA-256 characters>/sessions/session-*/runs`. Read session paths
from metadata instead of constructing `<hash>/firmware.elf`. Existing schema 1
packages remain supported; API_VERSION=1. Source directories are retained for
diagnostics; no automatic cleanup occurs. Remove old builds only after preserving
required evidence and completing all runs that use those directories.

Previously, reopening a package removed the entire hash directory, including runs.
Lost JSON reports cannot be recovered from summary: verification must be repeated.

F401 baseline adds only a fixture and offline CI; API_VERSION=1 and schemas are unchanged. [F401](F401_CMSIS_BASELINE.md).

F401 ADC/DMA changes only the fixture. The shared F4 measurement function is now adc_convert_f4_factory, a test firmware symbol rather than public module API. API_VERSION=1 and schemas are unchanged. [F401 ADC/DMA](F401_CMSIS_ADC_DMA.md).

F401 RTC/Sleep extends only the fixture. rtc_f4.c and vectors are shared with F411; public API and schemas are unchanged. F411 was checked offline after the move. [F401 RTC/Sleep](F401_CMSIS_RTC_SLEEP.md).

Added fixture profile f429zi with seven cases. Public API, schemas and version are unchanged. [F429 baseline](F429_CMSIS_BASELINE.md).

F429 fixture adds ADC/DMA and arithmetic; shared converter, public API, schemas and version are unchanged. [F429 ADC/DMA](F429_CMSIS_ADC_DMA.md).

F429 uses the shared F4 RTC implementation and vectors; RTC algorithm, public API and schemas are unchanged. [F429 RTC/Sleep](F429_CMSIS_RTC_SLEEP.md).

[HAL F030: five GPIO/RCC techniques and source variants](F030_HAL_GPIO_RCC.md).

## Result journal capture (Unreleased)

Enable required capture in session.toml:

```toml
[results]
capture = true
```

The default is false; scenarios need no migration. Capsule/pack transports this setting;
prepare-only does not require a journal. After scenario return or exception, before close,
the runner saves all records() to records.json beside result.json. Target methods are unchanged.
Schema 1: schema, run_id, case_id, records (sequence/name/data). run_id is the opaque run directory
name (UTC, ID, PID). Limit: 16 MiB; publication replaces a fully written temporary file in the
same directory. Existing artifacts are refused. One run owns its directory; concurrent writes
by other processes are unsupported. There is no power-loss durability guarantee.

result.capture.status: saved/unavailable/error; completion: normal (return), interrupted
(scenario exception), unknown (scenario not entered or report not received). Saved includes path,
sha256, count; error includes {type, message}. The host verifies hash, ownership and schema.
result.status preserves the original verdict. command_code: PASS/FAIL/ERROR → 0/1/2;
required capture failure → 2, with a separate artifact_error. GDB exit matches status.
Forced termination may lose the journal; a missing artifact is never replaced with an empty file.

On capture failure JUnit adds an infrastructure testcase <ID>.capture with error, preserving the
original testcase. The tests count includes this testcase, not an additional MCU check.
Console output separates Scenario, Capture and Command. CSV/HTML are outside this stage.

## Saved result processing (Unreleased)

`results export` and `results verify`: [contract, CLI and examples](RESULTS.md).
The journal holds arbitrary data; measurement projections are defined separately. Target methods and existing scenarios need no changes.

`results report` builds standalone JSON/HTML from the index and optional export; [summary and themes](RESULTS.md#jsonhtml-summary-unreleased).

HTML summaries include theme and normal/expert view controls; data remains unchanged.

Composite techniques using the existing API: [events and intervals](TESTING_TECHNIQUES.md#tech-011), [waiting for changes](TESTING_TECHNIQUES.md#tech-015), [C++ context](TESTING_TECHNIQUES.md#tech-019).

### reach and C++ quotes (Unreleased)

Use the full signature for an overload. Fixed a false frame-name FAIL with one outer pair of GDB single quotes; unquoted strings work as before. No migration is required; the workaround for 0.3.0 is to omit outer quotes. [Contract](api/reach.md).


## SKIP (Unreleased)

[skip(reason)](api/skip.md) — inapplicable scenario completion; reason, records, code77 and migration.

## st-util and schema 2 (v0.4.0)

Select `backend = "st-util"` in the stand; target.toml schema 2 may include
`[st-util]` with `reset_halt = "monitor reset"`, or use the default.
Existing sections and scenarios need no changes. `profile.stand["backend"]` may
now be `st-util`; update consumer allowlists. Target methods and API_VERSION=2
are unchanged. [Configuration and limits](BACKENDS.md#st-util-v040).

## Remote server completion (v0.4.0)

In result.json, `status_before_cleanup` retains the outcome before recovery/cleanup. `remote_server`
contains actual POSIX `returncode`, `reason`, `signals`, `ssh_returncode` and `error` on failure.
For example SIGABRT is returncode -6 while SSH returns250. Unknown means null, not0.
Cleanup failure produces final ERROR and cleanup_error, retaining checks, original error and skip_reason.
Consumers must use final status; status_before_cleanup is diagnostic. Target API and API_VERSION are
unchanged. st-util requires exit0 after requested shutdown; SIGKILL, heartbeat timeout or missing
confirmation means ERROR. This does not guarantee USB-safe shutdown.

st-util adds `recovery_wait` (when recovery was needed), `shutdown_wait` and `remote_server.idle`,
each with `ready`, `reason`, `elapsed_s`, `limit_s`. The latter confirms idle observation on the stand
host; exit0 alone is insufficient. Listening waits are limited to5s, host recovery to10s, and the final
SSH wait to25s including cleanup. These fields are diagnostic: use final status for acceptance.
[Lifecycle](LINUX_STAND.md#shutdown-diagnostics).

st-util may end its marker with an ellipsis: `Listening at *:port...`. The parser accepts it; an incomplete line without a newline does not establish readiness.

External finite package dispatcher: [stand_loop](STAND_LOOP.md). Target API and existing run/pack commands are unchanged.
