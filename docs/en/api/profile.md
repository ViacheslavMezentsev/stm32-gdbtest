# profile

[API](index.md) · [Русский](../../ru/api/profile.md)

`profile: Profile` — a read-only `Mapping` over `target.toml` with run sections

| Property | Value |
| --- | --- |
| Module support | indexing: 0.1.0rc1 / v0.1.0-rc.1; sections, `get`, `origin`, `to_dict`: 0.3.0.dev0 (core) |
| API specification contract | indexing: 0.1.0; sections: 0.3.3 |
| API_VERSION | 1 (indexing keeps the published contract) |
| Replaces | `config`, `config_props`, `settings`, `sources` (removed in 0.3.0 without aliases) |
| Basis | the verification firmware `tests/firmware`, scenarios `HW_CI_PROFILE`, `HW_CI_ADC_SERIES`, `HW_CI_RESET` |

## Purpose

Describes the run the scenario executes in: the target, the effective API settings and scenario
parameters, the image policy, the captured files, the current case, the stand and the GDB in use.

## Contract and limitations

- `profile[key]`, iteration and `len` read `target.toml` exactly as in 0.1 (`profile["flash_start"]`).
- Sections: `target`, `api` (effective `api.toml` with core defaults for `records`, `frames`,
  `execute`), `user` (the `[user]` table of `api.toml`), `image` (the selected policy or `None`),
  `files` (`{role: {reference, sha256}}` for `target`, `api`, `image`, `session`), `case` (`id`,
  `function`, `timeout_s`, `labels`, `contracts`), `stand` (`backend`, `server`, `speed_khz`, `flash`),
  `gdb` (`version`, `stop_details`, `value_history`, `type_is_signed`).
- `get(path, default=None)` reads a dotted path; a path without a section name reads `target.toml`.
- `origin(path)` reports where a value comes from: `{"state": "file", "file", "sha256"}`,
  `{"state": "default"}`, `{"state": "override", "variable"}` or `{"state": "run", "section"}`;
  a missing path raises `KeyError`.
- `to_dict()` returns a plain JSON-compatible copy for `record` and reports.

Every section and nested mapping is read-only (`TypeError` on assignment); arrays are tuples.
`gdb.stop_details` is `None` until the first stop, then `True` if this GDB reports stop details.
`files[...]["reference"]` does not promise that the path exists on another host.

## Example

```python
count = target.profile.get("user.measurement.count", 10)
if target.profile.stand["backend"] == "jlink":
    target.check("J-Link reset command", target.profile.get("api.reset.command"), "monitor reset")
target.record("run", target.profile.to_dict())
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.3, items 4.14.1–4.14.6.
- [record](record.md), [reset](reset.md).
