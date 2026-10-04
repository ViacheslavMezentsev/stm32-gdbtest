# config_props

[API](index.md) · [Русский](../../ru/api/config-props.md)

`config_props: Mapping`

| Property | Value |
| --- | --- |
| Module support | 0.2.0.dev0 → 0.2.0rc1 |
| Contract in API specification | 0.2.0; §4.12 |
| API_VERSION | 1 |
| Former-name alias | config_props -> sources (the alias works without warnings until 1.0; removal in 0.4.0) |

Implemented extension; `0.2.0rc1` is a local candidate, not a published stable release.

## Contract

Deeply immutable mapping of the same api/target/image roles. A file has data without defaults, original-byte sha256 and reference; absent files yield None.

Describes the same snapshot as config. data excludes TOML comments. reference does not guarantee a usable path on another host; do not reopen it to obtain the actual run configuration.

## Example

```python
source = target.config_props["api"]
if source is not None:
    target.record("config.api", {"sha256": source["sha256"], "reference": source["reference"]})
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

This is an illustrative fragment; no separate hardware run of it is claimed.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.12.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/host/test_target_records.py).
- [config](config.md), [record](record.md).
