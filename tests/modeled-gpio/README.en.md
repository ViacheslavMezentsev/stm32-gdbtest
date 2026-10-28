# Modeled GPIO: stimulus and override boundaries

[Русский](README.md) · [MMIO](../../docs/en/api/mmio.md)

Neutral API 3 example A5.2, without core changes or hardware. This is a diagnostic
GDB probe, not a new injection API or an ordinary `@case`. GDB runs on its main
thread. The existing external `tools/renode_probe.py` launcher owns the emulator;
the production Renode backend intentionally does not load arbitrary PythonPeripheral scripts.

## Evidence route

External source → teaching GPIO input → firmware volatile IDR read →
raw/active/neighbour/samples → independent analysis.

An atomically replaced `stimulus.json` is outside MCU address space. Inputs change
while the core is halted; the next peripheral access applies the new generation.
This discrete two-input model is **not STM32 GPIO** and proves no electrical level,
timing, debounce, EXTI, DMA or pull configuration. Hardware needs a separate experiment.

## Expected checks

- RO IDR write, including reason only: write_denied, no peripheral callbacks.
- Override without reason: refused before transport.
- Read-write override with reason: one ignored write, ACK with verified=false.
- False claim “override forces input high”: separate original FAIL (expected 1, consumed 0).
- External levels 2, 3, 3, 2, 3, 2: one firmware read each, active 0/1/1/0/1/0,
  neighbour bit always 1, increasing sample count.
- Normal completion and exception before resume: restore and read back the entire
  16-byte POD and input levels. Generation remains monotonic, not rolled back.

This model IDR is safe to read repeatedly. Do not generalize to read-to-clear/FIFO.
Override changes the access description, never device behavior. ACK/readback alone
does not prove firmware consumption.

## Run

```sh
python3 -m unittest discover -s tests/host -p test_modeled_gpio.py
python3 tests/modeled-gpio/run.py --toolchain <root> --renode <executable>
```

On Windows use `python`. Requires ARM GCC/GDB with Python, Renode 1.17 and host g++.
Linux paths used: `/opt/xpack-arm-none-eabi-gcc-14.2.1-1.1`, `/opt/renode-1.17.0/renode`.
Use a Docker volume for source and builds, as described in [local CI](../../docs/ru/local-ci.md).

`build/modeled-gpio/<run>/` preserves source hashes, ELF, compiler/debugger versions,
build command, independent `accesses.jsonl`, Renode version/log and GDB log.
`runs/probe-*/` holds observations, checks, result, negative-control and standard
capture/records verified through the common reader. Analysis PASS means the observed
outcomes match expectations, including a separate negative-control FAIL. Never turn
that FAIL into a successful assertion of the false claim. Process cleanup and restored
model resources are separate checks. The launcher bounds execution and owns its Renode.

Host tests exercise the shared C++ consumer, model and analysis rejection paths;
only Renode exercises actual GDB/RSP and firmware peripheral reads. The model declares
UTF-8 explicitly for IronPython.
