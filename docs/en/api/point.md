# point

[API](index.md) · [Русский](../../ru/api/point.md)

`Point: id, location, addresses, active, hit_count; remove(); with`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.9 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Represents a set point and its state: identifier, location, addresses, activity and the number of
hits.

## Contract and limitations

The object supports the context manager: leaving the block removes the point.

Limitations: the hit counter depends on the backend; addresses apply to software points; repeated
removal is not an error, while accessing a removed point produces diagnostics.

## Example

```python
point = target.breakpoint("board_led_toggle")
target.reach("app_loop")
target.check("stopped at the point", point.active, True)
point.remove()
```

After removal, accessing point properties reports a failure instead of stale data.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
