# API, CLI and integration

[Documentation](index.md) · [Русский](../ru/API.md)

This page describes **0.5.x / API_VERSION=3**. Operation contracts and support limits are
in the [reference](api/index.md); user-facing changes are in [release transitions](RELEASE_CHANGES.md).

## Configuration and execution

Prefer CMake `SESSION_CONFIG` and an explicit session.toml `[config]`:
select `target`, `api`, `image`, `[mmio].svd` and `[data]` according to their contracts.
[HIL structure and paths](HIL_INSPECT.md), [inspect](HIL_INSPECT.md), [SVD](SVD.md).
Do not combine SESSION_CONFIG with PROFILE or a separate image policy.
`t.profile` exposes immutable configuration and origin; `record`/`records` hold one
scenario's journal. Enable `[results] capture = true` to save it to a file.
[Capture and export](RESULTS.md) are checked separately from scenario outcome.

Ordinary `def` uses synchronous navigation and `call`; `async def` requires `await` for them.
`resume(sync=False)` starts a live window, `await wait()` waits, `await halt()` stops.
Data access requires confirmed halt. `ret` and data methods are immediate; `execute` is
forbidden in async. [Full contract](LIVE_EXECUTION.md).

Use `t.mmio.read/write` with SVD for peripherals. Ordinary `write` is not a safe MMIO
replacement; hidden function calls in data expressions are forbidden. [MMIO](MMIO.md).
`memory` requires a complete response and `write` evaluates RHS once; neither rolls back
all side effects. C++ preflight does not extend the names accepted by `call`.

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

## A1 migration towards 0.6.0

API_VERSION remains 3. MMIO accepts reason without override. Primary execution/transport
errors survive audit failure; separate diagnostics and cleanup confirmation are described
in [resume](api/resume.md), [MMIO](api/mmio.md), and [RecordError](api/record-error.md).
Failed execution auditing after a successful operation now raises ApiError/journal_unavailable
instead of bare RecordError. Limits, capture and record format are unchanged.

## A2.1: compact journal (0.6.0 candidate)

Select API schema 2 in `api.toml`; schema 1 keeps its previous defaults and limits.
The default representation is `full`; compact MMIO is explicitly enabled:

```toml
schema = 2
[journal]
representation = "compact"
[records]
max_records = 65536
max_nodes = 2097152
max_text_bytes = 16777216
```

These three values are maxima for long series, not defaults.

| Parameter | Schema 2 default | Schema 2 maximum |
| --- | ---: | ---: |
| max_records | 4096 | 65536 |
| max_nodes | 131072 | 2097152 |
| max_text_bytes | 1048576 | 16777216 |
| max_depth | 16 | 32 |
| max_integer_bits | 256 | 1024 |

Compact MMIO stores original/effective/SVD SHA-256 once in a definition table;
events carry a reference and an operation ID. Order, values, reason, override,
attempt and result are preserved without aggregation. A missing result is not
success. User `record("mmio.attempt", ...)` remains a user record. Node/text
budgets count encoded storage, including references and definitions; encoding
does not increase logical data depth. These are not RSS, latency or retained-copy limits.

`records()` returns detached logical sequence/name/data rows as before.
Compact materialization is bounded by 2097152 nodes, 16 MiB text, depth 32 and
1024 integer bits. Exceeding a budget raises RecordError with
`details.scope="materialization"`, without a partial list. Encoded storage may
fit while expanded rows do not: filter by name and avoid querying on every iteration.

With `[results] capture=true`, full writes `records.json` schema 1, compact writes
schema 2 with definitions. Capture serializes chunks without expanding the whole
journal. The common `stm32_gdbtest.result_capture.read(directory, report)` reader
validates both formats and returns logical rows; `materialize=False` expands one
row at a time. Encoded JSON is still loaded into memory: this is not a streaming
JSON parser or a constant-RSS guarantee. Validation covers hashes, run identity,
sequence, references, operation pairs and event fields. The independent records
file cap is 64 MiB; an oversized artifact causes capture failure without changing
the scenario verdict. Other exporter JSON input limits remain 16 MiB. Older
consumers need an updated reader for schema 2.

Migration is opt-in. API_VERSION stays 3; API configuration, records and capsule
schemas are distinct. Runner/packages validate the schema-specific defaults and
maxima fingerprint. Execution, timeouts and MMIO transport counts do not change;
summary/truncate are outside this package.

[Reproducible benchmark](../../tests/mmio-renode/README.md) and
[A2.1 measurements](../development/journal-a21-measurements.md).

## Result journal and output (0.6.0 candidate, A2.2)

An API schema 2 file can independently select result storage and console output.
Both options default to `full`:

```toml
schema = 2
[report]
representation = "compact"
console = "failures"
```

Compact storage retains **every** check, stop, mutation, evaluation, execution and
reset in order. `report_schema=2` is separate from the records.json schema.
Checks still execute; catching CheckFailed does not turn failure into success.
`failures` suppresses PASS lines and the full stdout/JUnit JSON copy, retaining
errors, warnings and a summary linking to result. It does not filter checks.
The derived `execution_summary` is not independent evidence: a wait timeout neither
closes a live window nor proves the target stopped.

The shared reader validates block hashes, references, logical counts and completeness:

```python
from stm32_gdbtest.report_data import read
report = read("result.json")  # schema 1/2 validation, then ordinary lists
report = read("result.json", materialize=False)  # sequential collection traversal
for check in report.get("checks", []):
    print(check["name"], check["passed"])
```

Export to a new full-format file for older consumers:

```console
python -m stm32_gdbtest.report_data result.json result-full.json
```

Using plain json.load on compact results and evaluating only status is **incorrect**:
it bypasses collection decoding and integrity validation. The runner, coverage,
result-index, export and stand-loop use the shared reader. report_storage_error or
report_audit_error_count makes evidence ineligible; the scenario verdict remains
separate from artifact failure and command exit status.

Compact mode spools completed events at 128 rows or 1 MiB of accumulated JSON
bytes per block; a single larger row is allowed separately. reach commits
its stop after frame completion; write commits after readback, including failure.
Changing a returned dictionary does not rewrite compact history. Accumulation adds
no GDB/MMIO reads or repr calls. Opaque Python/GDB values retain late repr semantics
at final serialization, with at most 128 deferred rows per collection. Prefer plain
JSON values for predictable snapshots; user-defined repr is not guaranteed pure.

Compact budgets: 65536 rows per collection, 16 MiB file, 64 MiB expanded rows,
64 MiB spool per collection, document depth 40 and 2097152 encoded JSON nodes.
The plain pending buffer holds at most 128 rows, but row size, deferred objects and
final serialization also consume memory; constant RSS is not promised. Budget or
I/O/integrity failures are explicit, never truncation. Result publication is atomic.
Primary and audit failures remain separate; incomplete history cannot produce PASS.

Tests: `tests/host/test_report_data.py`, `tests/renode-backend/run_report.py`.
The shared reader and full publication also enforce the 16 MiB file limit.
Full mode retains its structure; JSON whitespace is not part of the contract.

## Summaries and output levels (A2.3, 0.6.0 candidate)

In API schema 2, `[report] console="summary"` adds grouped terminal/JUnit output.
Existing full/failures levels and the default full remain unchanged. Storage selection
(full/compact) is independent: every check executes and every event is retained.
There are no new Target methods and no journal truncation.

The runner builds summary.json (schema 1, derived=true) after publishing final result,
using the shared result/records readers. Rebuild or verify offline, without GDB:

```console
python -m stm32_gdbtest.report_summary build/run/result.json
python -m stm32_gdbtest.report_summary build/run/result.json --verify
```

The first command explicitly replaces summary.json beside result; the second checks
schema, source hashes and equality with recomputation. Both print JSON. Python APIs:
report_summary.build(path) (no writes), write(path), read(path) (validated saved view).
Offline commands never change source evidence. A failed rebuild removes the old view.

Scenario, capture, cleanup and command outcomes remain separate. Collections contain
exact counts of **recorded** events, groups and zero-based collection references;
execution references use records.sequence (one-based). Missing collections say
not_recorded, not zero physical operations. User measurements are never implicitly
averaged. Check groups flag different_expectations; a middle FAIL always contributes
and failed groups/references are prioritized.

analysis=complete means requested sources are available and verified for this view,
**not** sufficient for a DDTT claim. Missing/corrupt records, audit errors or insufficient
generation information produce partial with reasons. Runtime execution_summary is not
used as proof of persisted events. Wait timeout never closes a window; generations
remain separate. closed denotes an observed stop; opened=false denotes no recorded
start for that window. Errors without generation remain unresolved. Host time is not
converted to MCU time.

Presentation limits: 100 groups per collection, 20 references per group, 100 windows;
omitted counters disclose hidden presentation. Counts include the entire source.
Labels/diagnostics have 256-character previews, shortened flags and full-text hashes;
references identify full result fields, and normal error output retains full errors.
The summary file limit is 1 MiB; result/records budgets are unchanged. Group display
limits do not bound builder memory independently of input budgets; constant RSS is
not promised.

Builder/publication failure adds summary_error without changing the scenario verdict
or events, sets command code 2 and a JUnit infrastructure error. Terminal/JUnit show
analysis=unavailable. Invalid source-result makes offline CLI fail without a new summary.
DDTT export still consumes primary evidence; a summary cannot replace ordering, timing
or restoration checks.

Correct: navigate from a summary to an event and assess its conditions. Incorrect:
use first/last as complete history, partial as a full journal, or confirm coverage
from summary status/success counts alone. Tests: tests/host/test_report_summary.py and
tests/renode-backend/run_report.py --summary.

A2.3 boundary: mutations do not always carry an independent per-operation verdict.
For non-check collections failed=null means not classified as a check, not zero
failures. Consult events and diagnostics; mutation counts do not prove successful
writes/restoration. --verify can successfully validate a partial view: exit 0 confirms
integrity, not applicability; inspect analysis and issues. JSON types remain distinct.

Counters describe stored rows, not physical events: one stop may appear in multiple
diagnostic stop entries. No speculative deduplication is performed; physical event
counts require a separate analysis.

## Strict completeness (A3.1, 0.6.0 candidate)

No new settings or truncation are enabled: `on_limit` is not supported yet. API
schema 1/2, API_VERSION=3 and full/compact formats remain supported. Result gains
`evidence` (schema=1, policy=error) and `check_accounting`, additive strict-mode
metadata rather than the future A3.2 lossy-storage schema.

Checks/stops/mutations/evaluations/executions/resets and the used records journal
track attempted/saved/lost, state=complete/unavailable, and first/last lost attempt
numbers. These are storage-attempt ordinals, not MCU time; the interval does not
mean every event within it was lost. Serialization fallback retains executed check
counts while setting saved=0 for discarded collections. Legacy metadata absence
is not a new completeness claim; original files are not supplemented.

`check_accounting` counts total/failed/unclassified before storing the detail row.
A caught CheckFailed remains FAIL even if that row cannot be saved. A caught lost
record prevents normal scenario completion from becoming PASS. Execution errors,
capture, cleanup and command outcomes remain separate; incomplete evidence gives
command code 2. SAVED means file publication, not complete observations. Invalid
types/depth are validation refusals; cumulative records/nodes/text_bytes exhaustion
is a lost record. A `records()` materialization limit is not a new journal event.

The independent `evidence.diagnostics` reserve retains the first 16 bounded details,
up to 64 KiB JSON, then only diagnostics_total/diagnostics_omitted. It does not retain
user values. Existing A1 diagnostic fields remain for compatibility: this budget
is not a whole-report or RSS limit. Cleanup does not depend on reserve capacity.
Process loss, memory exhaustion or disk failure cannot guarantee fallback publication.

Shared result/records readers validate counter types, sums, loss ranges, saved rows,
check counts and reserve limits. Summaries expose execution counts separately from
stored details and become partial on loss. DDTT export conservatively blocks
confirmation from incomplete results. Correct: inspect completeness, source rows,
conditions and cleanup. Incorrect: interpret empty checks as zero executed checks,
code 2 solely as firmware FAIL, or SAVED as proof of completeness.

### Configurable and fixed budgets

`[records]` in api.toml configures max_records/max_nodes/max_text_bytes/max_depth/
max_integer_bits within schema bounds. `[journal]` and `[report]` select storage;
report.console selects output. Maximum bounds, file limits (records 64 MiB, result
16 MiB), collection/materialization limits, reserve and summary limits are currently
fixed in code. User accumulation budgets differ from defensive reader limits.
A3.1 neither raises them nor adds unified quota configuration; this is a separate
A3.2 decision. Patching limits inside a scenario is not a supported public API.

A compact collection's `complete=true` confirms intact stored rows, not absence of
lost observations; consult `evidence.stores` for that. Analyze records.json together
with result.json, which carries completeness and outcomes. Check counts include
runner checks as well as user checks.

[Journaling](JOURNALING.md): sources, budgets, completeness, routes and schema 3 journal execution availability.

## A3.2: journal quotas and truncation

In the 0.6.0 candidate, API schema 3 executes `journal.on_limit="error"|"truncate"`.
The `[records]` budgets bound accumulation. Exhausting records/nodes/text_bytes under
truncate preserves whole prefix records and stops detailed storage until scenario end.
Checks, MMIO, live execution and cleanup continue. Completeness becomes `truncated`,
without changing the scenario outcome by itself: PASS with command=2, SAVED capture
and partial analysis is possible. Incomplete runs cannot confirm DDTT claims.

`records(name=None, *, require_complete=True)` raises `RecordError`/`incomplete_evidence`
for an incomplete journal, including named queries. Explicit `require_complete=False`
returns the stored prefix with original sequence numbers; it does not certify completeness.
Invalid types, cycles, depth, integer width and hard validation resource ceilings are
errors, not truncation. Inputs remain validated after detailed storage stops.

MMIO descriptors and attempts commit atomically. An attempt whose result did not fit
proves neither success nor absence of effects. Truncation adds no register reads/writes.
Transport/storage errors are not suppressed. The first loss cause, attempted/saved/lost
and first_lost/last_lost remain in evidence; diagnostic storage remains bounded.

Truncate policy uses evidence schema 2, result schema 3 (full/compact), and records
schema 3 with completeness checked against result. Old readers reject these formats.
Use the module shared readers. Report quotas/truncation are executable too; see the section below.

## A3.2: report quotas and truncation (0.6.0 candidate)

API schema 3 applies report.max_rows_per_collection independently to checks, stops,
mutations, evaluations, executions and resets, in full and compact storage. Range:
1–65536, default 65536. report.on_limit="error" refuses overflow; "truncate" preserves
each collection prefix without stopping other collections, journal, checks or cleanup.
Journal/report policies are independent; all validated combinations are executable.

Attempted continues increasing, saved is the prefix length, lost and first_lost/last_lost
identify the omitted tail. The bounded reserve retains the first cause per collection.
Independent check_accounting counts all outcomes: catching exceptions or dropping rows
cannot erase FAIL. Summary groups describe saved rows; check_accounting retains full
outcome counts. Scenario PASS is possible, but command=2, analysis=partial and DDTT
confirmation is blocked.

Only the row quota is suppressed, never spool, serialization, transport or recovery
errors. If the saved prefix cannot be read/published, state becomes unavailable while
the initial truncation cause and independent counts remain. Dropped payloads are not
materialized: no repr or lazy GDB read is invoked for an omitted row. Missing rows
therefore do not certify the validity of their values.

Report truncation uses evidence schema 3 (report-truncate/both-truncate), result schema 3
and records schema 3. Readers unaware of this evidence schema reject it. Journal-only
truncation retains evidence schema 2; legacy strict formats remain readable. Report
truncation does not make a complete journal incomplete: records() checks journal
completeness, whereas whole-run analysis considers every store.

```toml
schema = 3
[journal]
representation = "compact"
on_limit = "error"
[report]
representation = "compact"
console = "summary"
on_limit = "truncate"
max_rows_per_collection = 1000
```

This explicitly selects a partial report. For complete acceptance evidence, keep error
and choose a sufficient budget. Example: tests/renode-backend/run_report_quota.py;
regressions: tests/host/test_report_truncate.py. No physical boards are involved.

## A3.3: consumers of incomplete evidence

`results export` checks all stores before projection. Incomplete sources produce no
records.csv/measurements.csv rows: diagnostics and command=2 explain the refusal.
Original result/records and scenario PASS/FAIL/ERROR remain unchanged. Explicit prefix
inspection uses shared records readers plus evidence metadata, not ordinary acceptance
projections. A complete journal does not make a truncated report a complete run.

The index retains verdicts and adds an incompleteness diagnostic; HTML displays it
separately from integrity. Intact files and SAVED do not prove completeness. Summary
collections show truncated/unavailable; groups count stored rows, check_accounting
counts all outcomes. DDTT/LCOV retain UNKNOWN without DA, never a misleading zero.

Rebuild derived summary/index/campaign after reader updates: old summaries may be stale.
Pack transports configuration, not a guarantee of future evidence completeness. The PDF
skill renderer consumes prepared evidence; authors must check completeness before
transferring measurements into its input document.

Offline replay: `python tests/renode-backend/replay_consumers.py --runs <campaign>/runs --output <new-directory>`.
Host matrix: test_partial_consumers.py (full/compact, journal/report/both, PASS/FAIL,
unchanged sources and a complete-source positive control).

## A4.1 — namespace/static (0.6.0)

The name is a plain identifier or a qualified namespace/static name, such as
`demo::increment` or `Probe::twice`. In the 0.6.0 candidate, a qualified call requires
one symbol with callable code and DWARF. Overloads are refused before execution
(`ambiguous_function`), instance methods produce `unsupported_method`, missing
symbols/code produce `function_unavailable`. `object.method` remains `invalid_function`.
Qualified calls support integer/bool arguments and integer/bool/void returns;
arity, range and types are checked. Pointers, references, float, variadic functions,
template names and implicit ABI arguments are not supported yet.
Expression strings produce `unsupported_argument` for plain functions too.
Preflight does not prove execution safety. Resolution uses `may-call-functions off`,
then the selected linkage symbol is called; `expression` shows that symbol while
`function` retains the caller's name. There is no automatic retry.

Migration: replace string arguments with previously obtained numbers; execute additional calls explicitly and use return_value. this/signature were not implemented at A4.1; the current A4.2 contract follows below.

## A4.2 — this / signature (0.6.0)

`call(function, *args, this=None, signature=None, timeout=None)` supports an explicit
object and exact overload selection in the 0.6.0 candidate. Use await in async def.
`this="&probe"` takes the address of a named object; `this="probe_ptr"` uses a named pointer.
Qualified variable names are allowed. Member/index paths, arithmetic, casts and calls
in this are not supported yet. The pointer is read once; object address, size and
alignment are checked. Both the object and pointer-variable storage must lie in the
ordinary SRAM window 0x20000000–0x20100000 (exclusive upper bound).
This routing restriction does not prove memory presence/ownership or object lifetime.
The author must reach object initialization and choose a safe execution context.

`signature="unsigned int(unsigned int) const"` specifies return type, explicit parameters
and method qualifiers. Do not include this; use `()` for zero parameters.
Named types/typedefs are resolved by GDB and compared against DWARF types. An overload
without signature remains ambiguous_function; no match produces signature_mismatch;
invalid syntax produces invalid_signature. Multiple exact matches are also refused.

The object type must match exactly or select a base under A4.3b; const/volatile are never discarded. An incompatible
object type produces this_type_mismatch, dropping qualifiers produces this_qualifiers,
null/MMIO/misaligned addresses produce invalid_this. this on static/free functions
produces unexpected_this. Non-virtual inheritance is described in A4.3b. Polymorphic types, ref-qualified methods,
constructors/destructors, operators and template names are outside this subset.
A4.1 scalar returns remain; explicit Pointer/Reference arguments are described in A4.3a. const does not imply side-effect freedom; volatile does not
provide MMIO transport guarantees.

Resolution does not execute target code; the selected linkage symbol is called with
the captured this value. Results and mutations retain this, this_address, this_type,
requested_signature, resolved_function and resolved_signature where applicable.
An unfinished dummy frame is not reported as restored context; side effects are not
rolled back automatically. An async request remains lazy until await.

```python
result = await t.call("Probe::choose", 2, this="&probe",
                      signature="unsigned int(int)", timeout=2)
t.check("selected overload", result["return_value"], 5)
```

## A4.3a — Pointer and Reference (0.6.0 candidate)

`from stm32_gdbtest import Pointer, Reference`. These are immutable descriptions,
not addresses or GDB expressions; construction does not access the target. Resolution
happens at call, and only at await in async, with the core stopped.

- `Pointer("samples", count=4)` starts at a named array; count cannot exceed its DWARF extent.
- `Pointer("buffer_ptr", count=4)` reads a named pointer variable once per argument.
- `Pointer("&state")` addresses one named object; count above 1 is refused.
- `Pointer.null()` explicitly passes null to a pointer parameter; null read from a variable is refused.
- `Reference("state")` binds an existing named object without temporaries or user conversions.

Count is in elements, defaults to 1, and accepts integers 1..1048576, not bool.
Explicit null uses count=0. Names are limited to 256 characters and may be qualified.
Member/index paths, arithmetic, casts and calls are unsupported. Bad descriptors
produce invalid_argument.

One T*/T& level supports integer, bool and non-polymorphic class/struct types with inheritance as specified by A4.3b below. Types must match exactly or select one unambiguous base; const/volatile may be added but never removed
(argument_qualifiers). Signatures accept these types and typedefs; overload selection
remains explicit. Descriptors also enable DWARF checking for plain C functions.
T**, void*, function/member pointers, T&&, array references, by-value objects and
pointer/reference returns remain unsupported. An integer is never inferred as an address.

Before execution, size, alignment and the entire ordinary SRAM range
0x20000000–0x20100000 are checked; pointer-variable storage is checked before reading
its value. Errors include argument_range, argument_type_mismatch, argument_qualifiers
and unsupported_argument. Arrays/objects have extent=known; pointer ranges have
extent=declared: the stated count does not prove allocation, ownership or lifetime.
Count does NOT constrain the function body or automatically bind a separate length
argument. MMIO/Flash are excluded.

Arguments retain JSON descriptions; argument_bindings stores path, actual/expected
type, address, count, bytes and extent. Null has zero address/size.
The module adds no post-call content snapshot. Scenarios explicitly check effects,
neighbouring data and restoration. This is not a guarantee of physical GDB-server
access counts; Reference uses dereference of the resolved address in the call expression.
All arguments are checked before the single explicit call; refusal does not invoke it.

```python
from stm32_gdbtest import Pointer, Reference

result = await t.call("demo::sum", Pointer("samples", count=4), 4,
                      signature="unsigned int(const unsigned int *, unsigned int)", timeout=2)
t.check("sum", result["return_value"], 10)
await t.call("demo::bump", Reference("scalar"), signature="void(unsigned int &)", timeout=2)
```


## A4.3b — non-virtual inheritance (0.6.0 candidate)

`call("Base::step", ..., this="&derived")` explicitly selects Base::step.
An exact non-polymorphic type or one unique path from the object's static type to
its base is accepted: single, multi-level and multiple non-virtual inheritance.
There is no inherited-name search for Derived::step: name the declaring class.
Overloads still require an exact signature.

The shared this/Pointer/Reference preflight reads DWARF layout, adds constant byte
offsets and passes the base subobject address. Pointer conversion to a base requires
count=1 even at offset zero: Derived[] is not Base[]. Exact types retain A4.3a rules.
Pointer.null() needs no adjustment; const/volatile can be added, never removed.

Both the source object and adjusted subobject are checked for SRAM range, size,
alignment and containment. Traversal is bounded to 128 nodes and 16 types per path.
Multiple paths produce ambiguous_base; missing, negative or non-byte offsets,
incomplete types and traversal limits produce base_layout_unavailable. Virtual
inheritance/polymorphic source objects produce unsupported_inheritance; existing
unsupported parameter/method refusals remain. Type, qualifier and range errors keep
their existing codes. All refusals precede execution (stage=validation, effect=none).

Validated on ARM GCC/DWARF and GDB using a neutral ELF. No dynamic layout or vtable
reads, downcasts, cross-casts, virtual dispatch or user conversions are supported.
public/private/protected access is not checked: this is debugger layout access, not
a compiler check of a C++ expression. Complete and trustworthy DWARF is a prerequisite;
corrupt metadata cannot prove ABI compatibility. Object lifetime, construction and
ownership remain the author's responsibility. Unknown layout is refused rather
than computed from target object contents.

Call results and audit add this_original_address, this_expected_type,
this_offset_bytes and this_base_path; this_address is the adjusted address passed.
argument_bindings adds original_address, offset_bytes and base_path; address/bytes
describe the passed subobject. The path lists types from source to expected base.
Explicit null has no path/original address.

```python
result = await t.call("Base::step", 3, this="&derived", timeout=2)
t.check("selected subobject", result["this_address"], expected_base_address)
await t.call("inspect_base", Reference("derived"), timeout=2)
```

Omit await in ordinary def. Do compare the address with an independent oracle,
check neighbouring fields and restore changes explicitly. Do not assume a second
base has offset zero, pass Derived[] as Base[], or bypass ambiguity with a cast
expression. Examples/refusals: tests/renode-backend/test_cpp.py, HW_CPP_INHERITANCE_*.


## A5.1 — applying and consuming substitutions

No API extension. Existing write/ret are exercised by the [neutral example](../../tests/controlled-input/README.en.md).
SRAM readback and ret.applied do not confirm consumption: continue to processing,
check the consumed value, branch, skipped effects and next ordinary input. ret is
not awaited; async navigation is. Include negative controls and explicit restoration.
Model PASS does not establish physical input or peripheral acquisition.

## Modeled GPIO input and override (A5.2)

The [executable example](../../tests/modeled-gpio/README.en.md) separates external
model input from SRAM/return substitution. Check source → register → firmware
consumption, the next input and an unaffected neighbour. `override` replaces the
SVD description, not device behavior: an ignored IDR write may receive an ACK.
Preserve the false claim as FAIL; separate analysis checks the expected lack of effect.
Restore both firmware state and external input. The model proves no electrical/timing properties.
