# Neutral C++ / GDB / Renode example

[Documentation](../../docs/en/index.md) · [Русский](README.md)

Windows teaching route without a board: host fake → C++17 ELF in Renode → Python inside GDB.
Checks deferred persistence and method calls on an existing object. This standalone example is
not a stm32-gdbtest backend; it does not use regular Target, session.toml or result.json.
Never load this ELF onto hardware: its addresses and peripheral protocol are model-only.

## Requirements and commands

From the repository root: Python 3.11+, host C++17 `g++`, ARM GCC with GDB-Python and Renode 1.17 on PATH:

```powershell
# Cache contract only, without GDB or Renode.
python -B tests/renode-cache/run.py --host-only
# Four host tests of the deliberately limited model, without Renode.
python -B tests/renode-cache/test_model.py
# Full route: host and two independent Renode instances.
python -B tests/renode-cache/run.py
# Wrong expectation: must produce FAIL, exit 1; this is a successful negative control.
python -B tests/renode-cache/run.py --negative-control
```

GDB selection uses `--gdb`, `STM32_GDBTEST_GDB`, PATH and the module's existing toolchain search.
ARM `arm-none-eabi-g++.exe` must reside alongside it. `--host-cxx` and `--renode` accept executable
paths; quote paths containing spaces. Host g++ needs its DLLs available (its directory is usually
on PATH). This runner does not yet support Linux. Use a checkout path without spaces (generated resc commands use @path). Do not use Python `-O`: the GDB scenario uses
assertions and rejects execution when they are disabled.

Verified environment: Windows, Renode 1.17, ARM GCC 13.3.1, GDB 14.2.90/Python 3.11.4.
ELF compilation: `-O0 -g3`, no LTO, exceptions or RTTI. No network access or USB is required.

## Files and editing

| File | Purpose |
| --- | --- |
| run.py | Input snapshot, compilation, two runs, logs and owned-process cleanup |
| buffered_store.hpp | Teaching cache without heap: load/read/write/dirty/commit and readback verification |
| cache_suite.hpp, cache_host.cpp | Shared 24 checks and 15 additional host failure checks |
| cache_calls.cpp, cache.ld | Neutral ELF; local object and buffer remain alive at cache_done |
| scenario_cache.py | Readable GDB Python scenario: calls, data, counters and model limits |
| platform.repl, flash_model.py | Cortex-M4, RAM and simplified storage with MMIO |
| test_model.py | Separate host tests of model properties and deliberate gaps |

Start by editing an expectation in scenario_cache.py, not application firmware. It executes on
GDB's main thread; ordinary Python does not provide the gdb module. Select reset_handler's frame
before retaining object/adapter/buffer pointers. Never reuse pointers after their lifetime ends.
A GDB call executes CPU code, not a method on an object copy. MMIO experiments deliberately change
state afterwards: the application is not resumed and the machine is terminated.

## Assertions

- Before commit only the cache changes; afterwards exact page data and the store counter change.
- Repeating a clean commit does not write; an invalid range refuses without a backing store.
- The host fake injects partial writes, read failure and corrupt readback; dirty remains for retry.
  Changing a byte back need not clear dirty. The destructor does not persist changes.
- C++ calls preserve observed PC/SP; this is not verification of all registers or contexts.
- Erasing pages 127/128/255 preserves neighboring guard bytes.

Counters represent logical adapter operations, not physical transactions. Calls through
`gdb.parse_and_eval` do not establish `Target.call()` acceptance. RTOS/ISR/PSP, LTO and optimized
forced calls are unverified. GDB CP1252/MSP warnings remain in reports.

## Model and provenance

Neutral code was written for this example; no consumer application, Arduino or HAL code is included.
flash_model.py is an independent teaching implementation of the observed simplified MMIO protocol.
Names and offsets resemble STM32G4, but the model deliberately is not an STM32 controller.

| Property | Boundary |
| --- | --- |
| Memory | 512 KiB MappedMemory; ordinary memory writes do not model Flash physics |
| Erase | A 2048-byte page is filled with FF; selected bank/region boundaries checked |
| KEYR/W1C | Key sequence and flag clearing implemented |
| LOCK | CR writes can bypass the lock; reported NOT_SUPPORTED |
| PG/EOP | PG sets EOP without payload validation; reported NOT_SUPPORTED |
| Busy, ECC, endurance, power loss | Not modeled |

Negative checks characterize gaps, not expected hardware behavior. Revisit expectations and limits
when improving the model. It is not a HAL driver validation model.

## Results and reproducibility

Each run creates `build/renode-cache/route-<UTC>-<id>/`: inputs (pre-build snapshot), ELF, GDB/resc
commands, raw stdout/stderr `.bin`, readable logs, summary.json and artifact-sha256.json.
Tool paths and hashes stay local. Earlier runs are never overwritten.
`schema=renode-cache-example-1` is an example format, not the module's reporting contract.

Exit codes: 0 PASS, 1 assertion FAIL, 2 preparation/tool/cleanup ERROR. Negative control changes
expected stores from 1 to 2. Missing GDB should produce ERROR without starting a machine.
Inspect cycles, model_properties and warnings, not only exit status; absent properties are not PASS.
Host-only PASS establishes only the cache contract. Reports do not enter module hardware acceptance
or aggregate reporting.

Renode starts hidden; readiness comes from logs rather than a TCP probe. ELF loading precedes GDB
server startup; GDB uses `-nx -nh`, a temporary breakpoint and disconnects. Afterwards the runner
sends quit, terminates only its own process tree if necessary and checks port release. Free-port
selection has a race window; attaching to unrelated servers is not intentional. Manual cancellation,
hung compiler trees and interactive debugpy debugging are not accepted. Example files and timeouts
do not introduce module TOML/CLI contracts.

See [TECH-019/020](../../docs/en/TESTING_TECHNIQUES.md#tech-019),
the [DDTT route](../../docs/en/DDTT.md#sandbox-route) and [checklist](../../docs/en/SCENARIO_CHECKLIST.md).
Define the contract and obtain a detectable FAIL first; after fixing it, repeat the same set and
preserve the original FAIL. Emulator PASS does not replace an agreed hardware experiment.
