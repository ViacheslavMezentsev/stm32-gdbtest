# settings

[API](index.md) · [Русский](../../ru/api/settings.md)

`settings: Mapping`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.3.0 |
| API_VERSION | 1 (the effective contract does not change) |
| Former-name alias | `config`; the alias works without warnings until 1.0, removal in 0.4.0 |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Gives the scenario read-only access to the effective run settings.

## Contract and limitations

A read-only mapping is returned; it cannot be used to change settings.

Limitations: the key set and its defaults are still being agreed; nested mappings are read-only as
well; a missing key produces diagnostics, not an empty value.

## Example

```python
timeout = target.settings["timeout_s"]
target.check("timeout is a number", isinstance(timeout, int), True)
```

Settings are not changed from a scenario: changing them is the run configuration's job.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
