# execute

[API](index.md) · [Русский](../../ru/api/execute.md)

`execute(command) -> str`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Runs a debugger command and returns its text output to the scenario.

## Contract and limitations

The output is returned as a string; a debugger error is neither hidden nor repeated automatically.

The output limit defaults to 2048 characters with a maximum of 16384; on truncation the journal carries `truncated` and `output_sha256` of the full output.

Limitations: one string is one command, an embedded newline does not split commands and the rest of
the string is literal text; the shape and limit of the diagnostic journal are still being agreed;
commands that change debugger state remain the scenario's responsibility.

## Example

```python
registers = target.execute("info registers pc sp")
target.check("pc reported", "pc" in registers, True)
```

A command that changes debugger state is executed as given; no rollback is performed.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
