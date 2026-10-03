# Upper bounds for records configuration

[Research](index.md) · [Русский](../ru/config-bounds.md)

2026-10-03. Implemented the accepted API specification 0.2.1 bounds in the research `session_config.py`. The contract and core remain unchanged.

| Parameter | Default | Inclusive range |
|---|---:|---:|
| max_records | 128 | 1–1024 |
| max_nodes | 4096 | 1–32768 |
| max_text_bytes | 65536 | 1–524288 |
| max_depth | 8 | 1–32 |
| max_integer_bits | 256 | 1–1024 |

Only exact integers are accepted, excluding bool. An invalid known parameter produces ConfigError with code api_parameter, its name and range before MCU execution. This is a configuration error, not runtime RecordError. Unknown fields and sections remain in config/config_props; identically named keys in custom sections do not inherit records constraints.

Tests use an independent expectation table: 45 invalid values (nine per parameter), 15 valid values (minimum/default/maximum), and three default paths (no api.toml, no records, empty records). Unknown values are retained. Snapshot transport tests cover five maxima and five excessive values with correctly recomputed SHA256: the receiver repeats semantic validation; the outer transport error retains the api_parameter cause.

Windows: 91 tests, 90 PASS and one platform CMake skip. Linux Docker CI: 91/91 PASS, including legacy mode and existing paired scenarios. Defaults remain unchanged. Hardware runs were not repeated: this step validates configuration before connection. Previous hardware acceptance is in the [three-board report](techniques-three-boards.md).

Bounds are enforced by the configuration loader. The private research Journal constructor does not become public API and does not duplicate configuration maxima. Integration needs one configuration validation path. The transport fingerprint checks defaults, not every validation rule; receivers apply their current rules.

Next: discuss first-package core integration using the [readiness matrix](readiness.md), followed by separate implementation and acceptance against the real Target. Integration is not yet authorized.
