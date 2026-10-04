# sources

[API](index.md) · [Русский](../../ru/api/sources.md)

`sources: Mapping`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.3.0 |
| API_VERSION | 1 (the effective contract does not change) |
| Former-name alias | `config_props`; the alias works without warnings until 1.0, removal in 0.4.0 |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Describes the run inputs: scenarios, configurations and their integrity identifiers.

## Contract and limitations

A read-only mapping with paths and checksums is returned.

Limitations: the field set and the checksum algorithm are still being agreed; the data describes the
run inputs and does not replace the build manifest.

## Example

```python
digest = target.sources["scenario_sha256"]
target.check("scenario digest present", len(digest) > 0, True)
```

Sources describe the run; they do not verify its outcome.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
