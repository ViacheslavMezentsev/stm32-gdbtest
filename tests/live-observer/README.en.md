# Neutral live-window observer

[Guide](../../docs/en/LIVE_OBSERVER.md) · [Русский](README.md)

API 3 example: oracle → install VTOR/SRAM observer → `resume(sync=False)` →
`await wait()` / `await halt()` → assess → remove → repeat without reset.
Uses the standard runner and Renode backend; no core API extension.

From the repository root (PowerShell; variables refer to your installations):

```powershell
python -B tests/live-observer/run.py --toolchain "$env:STM32_TOOLCHAIN_PATH" --gdb "$env:ARM_GDB" --renode "$env:RENODE_BINARY"
python -B tests/host/test_live_observer_example.py
```

Linux uses the same arguments with `$STM32_TOOLCHAIN_PATH`, `$ARM_GDB`, `$RENODE_BINARY`.
Requires GCC 14.2.1 / Python-enabled GDB supporting API 3, and Renode 1.17.0.
Other compilers require successful prologue validation and renewed acceptance.
Output: a fresh `build/live-observer/<UTC>/`; `--out` selects another new directory.
`summary.json` assesses **8 expected outcomes**: 5 PASS, 2 intentional ERROR, 1 intentional
FAIL. `unsupported.json` lists four FPB cases unsupported by this model. A connection
error cannot substitute for an intentional exception. Original result/records remain
unchanged. Do not run the full set as an ordinary all-PASS campaign.

`prepare.py` only builds the package and manifest. Without `--allow-hardware`,
`campaign.py` only prints a plan. The F411 hardware route requires separate admission
and fresh verified backups; see the guide for the complete procedure and limitations.

Files: `neutral.c/ld` — workload and SRAM ownership; `hook.S` — wrappers;
`test_observer.py` — scenarios; `fpb_adapter.py` — bounded F411 remap;
`policy.py` — preconditions; `recovery*.py`, `gdb_recovery.py`, `transport.py` — external
recovery; `test_*.py`, `fpb_adapter_host.py` — tests without a board.

This is a teaching workload with controlled events, not a board/RTOS/DMA model.
Renode exercises shared Cortex-M3 instructions, not hardware FPB remap.
Observing function/ISR entries does not prove every source line or branch.

Three DDTT assertions: `view/lcov.info`; reasons and links: `view/ddtt-evidence.json`. See the guide for the mapping rationale.
