# Moving a consumer from 0.4.x to 0.5.0

[Documentation](index.md) → [Versions](VERSIONING.md) → Moving to 0.5.0 · [Русский](../ru/MIGRATION_050.md)

0.5.0 is the `API_VERSION=3` release. Ordinary `def` scenarios keep their synchronous form; hardware
target schemas 1/2 and stands need no changes. Migration is required where a scenario evaluates hidden
function calls inside expressions, uses `execute()` in an `async def`, or reads and writes peripheral
registers through GDB expressions. The steps below follow the migration of the demo consumers
[stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) and
[stm32-hwtest-blackpill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill).

## What changed for a consumer

| Area | 0.4.x | 0.5.0 | Action |
| --- | --- | --- | --- |
| API compatibility | `API_VERSION=2` | `API_VERSION=3` | Review scenarios with the table below; do not turn `def` into `async` without a reason |
| Expressions | Could call target functions implicitly | `may-call-functions off` for data methods, `ret` and navigation conditions | Move the call into an explicit `t.call(...)` and use the returned value |
| `async def` | — | Navigation and `call` are awaited; `execute()` is refused | Add `await`, remove `execute`, keep `finally` with `halt` ([contract](LIVE_EXECUTION.md)) |
| Peripheral registers | GDB expressions over addresses and macros | `t.mmio.read/write` over an SVD snapshot with access rights and effects ([mmio](api/mmio.md)) | `[mmio] svd` in `session.toml`, replace accesses, explicit `allow_effects` |
| Package | Configuration capsule schema 1 | Schema 2 when an SVD is set (schema 1 without it) | The package receiver must support schema 2 |
| Configuration | Checked at run time | Offline `inspect` command ([guide](HIL_INSPECT.md)) | Check every profile before prepare |
| Emulators | — | target schema 3 for Renode/QEMU ([Renode](RENODE.md), [QEMU](QEMU.md)) | Only for the new route; do not move hardware targets |
| Skills | Previous header | Agent Skills format, `metadata.version` 0.5.0 ([skills](../../skills/README.en.md)) | Refresh `.claude/skills` copies together with the gitlink |

## Steps

1. **Branch and gitlink.** A separate consumer branch; point the gitlink to tag `v0.5.0` (before the release,
   to the accepted candidate), then `git submodule update --init`. Read the module CHANGELOG section and
   this page.
2. **Skills.** Copy `modules/stm32-gdbtest/skills/stm32-gdbtest-*` into `.claude/skills/` again instead of
   editing the old copies.
3. **Build.** If scenarios or the SVD/ELF check rely on CMSIS types the code does not use, add
   `-fno-eliminate-unused-debug-types`; otherwise GDB does not see the register structures.
4. **SVD.** Set `[mmio] svd = "<path relative to session.toml>"` in every profile. A verified subset is fine
   (BlackPill uses 40 registers of a shared F4 description) when its source is recorded: RM/PM, licence,
   hash. Core registers may be missing from a vendor SVD: add a verified description or a limited override
   with a reason.
5. **Scenarios.** First inventory every `read`, `evaluate`, `write`, `check(rows)`, `memory` and dynamic
   expression that touches peripherals, not only matches by register name. Then move to `t.mmio`:
   - W1C flags with an explicit mask: check the error first, clear it afterwards;
   - registers with a read effect (SysTick `CTRL.COUNTFLAG`, FIFOs) and command bits (`SCB.ICSR`, NVIC
     `ICER`/`ISER`) without a general snapshot or RMW, with `allow_effects=True` only for a known effect;
   - write-only registers without a check read; DMA `NDTR` only while the stream is disabled;
   - `ret` injection, arguments, application fields and RAM stay with the general API.
   Every new expectation comes from the requirement or the RM, not from the board's answer.
6. **Records.** Each MMIO operation adds two journal records; with `[results] capture = true` check the
   records limit (`max_records` in `api.toml`).
7. **Without a board.** `inspect` each profile → build → `ctest --preset <profile>-host` (prepare,
   traceability, host migration regressions). prepare does not execute scenario bodies and does not prove the
   migration.
8. **Board.** One scenario, then the full `ctest --preset <profile>-hw` set for every profile. Earlier 0.4.x
   hardware runs are not acceptance of the new version.
9. **DDTT.** Rebind maps and anchors after scenario changes; keep the controls for a wrong tolerance and a
   missing record ([coverage](DDTT_COVERAGE.md), [qualification](DDTT_QUALIFICATION.md)).

If an operation cannot be moved, record a narrow exception and its impact instead of declaring the whole
project migrated.

## What is not needed

- Changing hardware target schemas 1/2, stand files or the Flash programming policy.
- Turning working `def` scenarios into `async def`.
- Replacing application memory accesses and injections with MMIO.
- Carrying 0.4.x results over to the new version: evidence belongs to its module revision.

Details: [API](API.md), [MMIO](MMIO.md), [SVD](SVD.md),
[0.5.0 acceptance matrix](../development/release-050-acceptance.md) (Russian).
