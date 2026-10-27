# Short Renode probes

[Documentation](index.md) · [Русский](../ru/RENODE_PROBES.md)


For an API 3 live window use [tests/live-observer](LIVE_OBSERVER.md): standard Renode backend, eight expected outcomes, four FPB cases explicitly NOT_SUPPORTED. A direct trampoline does not prove hardware remap.
`tools/renode_probe.py` owns a separate Renode/GDB session; it is not a module runner backend.
Requires Renode 1.17, Python-enabled GDB and ARM GCC. No board is used. The neutral
`tests/renode-startup` model has Cortex-M3, NVIC, Flash/RAM, no ADC/DMA.

```powershell
python tests/renode-startup/run.py --gdb "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-gdb-py3.exe" --cxx "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-g++.exe" --renode "C:/Program Files/Renode/renode.exe"
```

Use Linux paths for the same arguments on Linux. Inputs must be committed: fresh ELF build,
stop at ready, started=1, counter=3, call an existing object's method, counter=7, seal campaign,
export portable report. Each run uses a unique build/renode-startup directory. The owner pushes
the tested SHA before its source links become available online.

For a custom ELF:

```text
python tools/renode_probe.py --project PROJECT --elf FILE.elf --model MODEL.repl --scenario SCENARIO.py --map BOUND_MAP.json --runs RUNS --gdb GDB --renode RENODE --case EMU_CASE
```

The model must load independently, without someone else's server/port. The scenario runs on
GDB's main Python thread after attaching to the loaded ELF. Write JSON to DDTT_PROBE_RESULT:
status PASS/FAIL/ERROR and checks=[{name, passed}], where passed is boolean. Exceptions, missing
files, malformed checks or nonzero GDB exit yield ERROR. The external envelope uses mode=emulator,
purpose=automated; it does not extend the hardware runner's result schema.

Readiness limit is up to 30 s, GDB defaults to 30 s (--timeout up to 300), remote response 10 s.
Readiness uses the Renode 1.17 log; a probing TCP client does not occupy the GDB connection.
Dynamic port selection still has a bind race: failure yields ERROR, not a board connection.
Only the owned process tree is terminated; primary and cleanup errors remain separate.
Raw result/run/checks and logs stay in the attempt directory; public output stays separate.

Verify SP/PC, Thumb and memory paths. An ELF does not establish model fidelity. ADC/DMA/Flash
controllers require a suitable model or a board. A method call requires an existing object and
function body; inline/LTO can remove it. Closing Renode is not MCU recovery evidence. Include a
negative expectation and a repeat run.

`tests/renode-cache/run.py` remains a separate Windows C++ cache/limited Flash-model example
with a host control; its supported scope is unchanged. See the
[Renode skill](../../skills/stm32-gdbtest-renode/SKILL.md) and [DDTT reports](PORTABLE_DDTT.md).

Negative control: repeat with `--negative-control`. Expect FAIL, exit 1 and a red method-call point; the next ordinary run must PASS again.

## P1 validation

Renode 1.17 was checked on Windows and Linux: startup and a method call, 3/3. On Windows the negative control produced two confirmations and one failure (exit 1), followed by another 3/3 ordinary run. The existing C++/RAM/cache example also passed. Host regressions cover readiness failure and GDB timeout with cleanup. This does not validate UART, ADC/DMA or the six physical stands.

## Current contract examples

For API 3 use `tests/renode-backend` and the [state/ring-buffer example](../../tests/stateful-buffer/README.en.md).
They use the standard runner, preserve raw FAIL outcomes and check cleanup.
`tests/renode-startup/run_contracts.py` is a historical expert experiment, not a current
acceptance route: expressions containing hidden inferior calls are now forbidden.
