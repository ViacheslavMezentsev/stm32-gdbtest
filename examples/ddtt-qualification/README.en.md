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
