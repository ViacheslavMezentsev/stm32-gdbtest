# Neutral DDTT admission example

[Русский](README.md) · [Contract](../../docs/en/DDTT_QUALIFICATION.md)

```powershell
python examples/ddtt-qualification/run.py --out build/qualification-demo
```

Use a new directory. Open index.html for ten synthetic cases, raw outcomes and
applicability. Each case contains map.json, snapshot.json, result.json, admission.json
(except missing), view/ddtt-evidence.json and lcov.info.

This is a host model: the ELF hash is an explicitly synthetic marker, frequency was not
measured and no board was qualified. 16 instead of 25 MHz makes the dependent assertion
UNKNOWN; independent ready remains CONFIRMED. raw-fail with valid conditions stays FAILED.
Power loss, conflict, stale data, another instance and declarations instead of measurements
never turn green. optional-absent demonstrates proven absence of an optional capability.

fixture() illustrates measurement and map formats. The external organizer calls bind()
after the attempt without changing the original result. Real projects need actual
records/capture, a measurement chain, correct inputs_sha256 and preserved inputs.

## Renode: independent receiver journal

`run_renode.py` builds one neutral ELF and uses the standard runner for a preflight
and a main run in each case: nominal, second word dropped, nominal repeated.
Firmware reports three sends; PythonPeripheral independently records received words.
The scenario reads sender RAM only, never the journal or receiver state.

```sh
python examples/ddtt-qualification/run_renode.py \
  --cxx /opt/toolchain/bin/arm-none-eabi-g++ \
  --gdb /opt/toolchain/bin/arm-none-eabi-gdb-py3 \
  --renode /opt/renode-1.17.0/renode --out build/qualification-renode/run-01
```

Use corresponding Windows paths and `.exe` suffixes on Windows. Output must be a new
directory. Requires Renode 1.17, ARM GCC and Python-enabled GDB. The self-contained
REPL embeds the peripheral script; the backend does not load external peripheral files.

Expected: raw PASS in all three cases. Two received words make the dependent point
UNKNOWN/VIOLATED, while initialization stays CONFIRMED. Repeating nominal restores
CONFIRMED. This demonstrates an **applicability condition**: sender count alone does
not prove delivery. The map explicitly adds a receiver requirement.

Each directory retains `preflight-receiver.jsonl`, `snapshot.json`, main
`receiver.jsonl`, unchanged `result.json`, `records.json`, `admission.json`, map and
`view/lcov.info`, `view/ddtt-evidence.json`; the aggregate is `summary.json`.
`result_unchanged` is checked by hashing before/after export. Renode logs record its version.

The snapshot precedes the main attempt and is valid for 120 seconds. This is a bounded
claim for a fixed deterministic model: input hashes and the journal are compared again
afterward. Missing/corrupt journals or changed model inputs stop the experiment without
granting admission. No physical crystal, supply or wire delivery is measured; receiver
firmware, IRQ and DMA are not modeled. This is neither continuous physical monitoring
nor hardware qualification.
