# config

[API](index.md) · [Русский](../../ru/api/config.md)

`config: Mapping`

| Property | Value |
| --- | --- |
| Module support | 0.2.0.dev0 → 0.2.0rc1 |
| API specification contract | 0.2.0; §4.11 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |
| Former-name alias | config -> settings (the alias works without warnings until 1.0; removal in 0.4.0) |

Implemented extension; `0.2.0rc1` is a local candidate, not a published stable release.

## Purpose

Deeply immutable mapping of api/target/image for the captured run, with defaults applied. A property, not a method.

## Contract and limitations

An omitted api uses defaults; omitted image is None. Unknown api fields survive; lists become tuples and TOML types survive. Missing keys raise KeyError; mutation is forbidden. SESSION_CONFIG selects sources; access does not reload files.

For the example below, select api.toml from session.toml and supply these settings:

```toml
# session.toml
[config]
target = "target.toml"
api = "api.toml"
```

```toml
# api.toml
schema = 1
[user.measurement]
count = 10
```

## Example

```python
settings = target.config["api"]["user"]["measurement"]
count = settings["count"]
target.check("valid series count", type(count) is int and 2 <= count <= 20, True)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.11.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [config_props](config-props.md), [record](record.md).
