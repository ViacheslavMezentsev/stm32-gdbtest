# Renode: native local backend

[Documentation](index.md) → [Backends](BACKENDS.md) · [Русский](../ru/RENODE.md)

Added for 0.5.0. Each scenario owns a fresh Renode process and one single-core machine.
Validated route: Renode 1.17, Cortex-M3, Windows and Linux. Emulator PASS is not hardware PASS.
SSH, attach, keep and machine reuse are not supported yet.

## Configuration

Stand: [stand.example.toml](../../tests/renode-backend/stand.example.toml).
Use `schema=1`, `[emulator]` and `[renode]`; combining with `[probe]` is rejected.
`backend="renode"`; `executable` is a path or resolved through PATH.
`startup_timeout_s=15`, `shutdown_timeout_s=5`: positive numbers up to 60 seconds.
`platform` is a self-contained REPL path relative to the stand file. Includes, filename
and network references are rejected in this first adapter; SVD and Python models are not
loaded. This is an adapter restriction, not a Renode limitation. Platforms are trusted project code.

Target [schema 3](../../tests/renode-backend/target.toml) requires
`environment="emulator"` and `architecture="cortex-m"`. Memory fields, `name`, `mcu`,
`breakpoint_limit`, `fault_handlers`, `core_registers`, `diagnostic_registers` remain.
Hardware `identity` and `openocd_target` are absent and rejected for emulator targets.
Schema 3 with `environment="hardware"` retains mandatory hardware fields from schema 2.
Schemas 1/2 remain compatible. Stand and target environments must match.
HW_* names remain scenario identifiers; report metadata, not the prefix, determines the environment.

## Running and evidence

From the repository root, supplying tool paths:

```powershell
python tests/renode-backend/run.py --toolchain "$env:STM32_TOOLCHAIN_PATH" --renode renode
```

On Linux use the same command with your toolchain path. It creates session.json and a
local stand.toml in a unique `build/renode-backend/` directory, then runs prepare,
PASS, intentional FAIL, reset refusal, timeout and repeat PASS. summary.json checks
expected outcomes; intentional FAIL/ERROR artifacts are retained. The generated session
also works with `python -m stm32_gdbtest run --session <session.json> --test HW_EMU_STARTUP`.

Runner snapshots ELF/REPL, starts Renode, loads ELF, checks GDB/halt, a single CPU thread
and file-backed Flash LOAD sections. It does not claim byte verification of BSS/arbitrary
RAM. Full Flash programming policies are rejected. Scenarios start at main;
`[results] capture=true` enables normal records.json capture.
Results use `mode="emulator"`, `environment="emulator"`, `hardware_accessed=false`;
model hash, Renode version and image-verification scope are retained. Keep emulator
and hardware DDTT evidence separate unless explicitly selecting environments.

Completion, error and timeout terminate owned processes and check the GDB port closes.
Cleanup failure produces ERROR; status_before_cleanup retains the preceding verdict.
Scenario timeouts use host time. Failed scenarios are not automatically retried.
`reset()` refuses with unsupported_backend, stage=validation, effect=none: a fresh
process does not substitute for in-scenario reset semantics. Start a new scenario for
fresh state. Arbitrary execute() remains an expert escape outside this guarantee.

## Networking and future reuse

Runner connects to 127.0.0.1, but Renode's GDB server may listen on all interfaces.
Loopback-only is not guaranteed: this is an accepted first-version limitation. Runner
never modifies firewall rules. Use environmental isolation when needed, such as a
container without networking.

Reloading ELF does not clear peripheral/event state. Future acceleration may reuse an
owned process while recreating its machine, with explicit isolation tests. keep is
currently rejected; preserving machine state needs a separate contract.

[QEMU](QEMU.md) — a separate minimal backend.


## P3 live-window verification

`python tests/renode-backend/run.py --toolchain <xPack-directory> --renode <Renode>`
also checks async scenarios in [test_live.py](../../tests/renode-backend/test_live.py):
early breakpoint, passive timeout, two windows, repeat, FAIL/ERROR/SKIP and halt on
completion. A breakpoint on a neutral function represents a fault guard; it does not
claim a physical Cortex-M exception. See the [contract](LIVE_EXECUTION.md).
