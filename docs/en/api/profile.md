# profile

[API](index.md) · [Русский](../../ru/api/profile.md)

`profile: Profile` — a read-only `Mapping` over `target.toml` with run sections

| Property | Value |
| --- | --- |
| Module support | indexing: 0.1.0rc1 / v0.1.0-rc.1; sections, `get`, `origin`, `snapshot`: 0.3.0.dev0 (core) |
| API specification contract | indexing: 0.1.0; sections: 0.3.3 |
| API_VERSION | 1 (indexing keeps the published contract) |
| Replaces | `config`, `config_props`, `settings`, `sources` (removed in 0.3.0 without aliases) |
| Basis | the verification firmware `tests/firmware`, scenarios `HW_CI_PROFILE`, `HW_CI_ADC_SERIES`, `HW_CI_RESET` |

## Purpose

Describes the run the scenario executes in: the target, the effective API settings and scenario
parameters, the image policy, the project data files, the captured files, the build, the current case, the
stand and the GDB in use.

## Contract and limitations

- `profile[key]`, iteration and `len` read `target.toml` exactly as in 0.1 (`profile["flash_start"]`).
- Sections: `target`, `api` (effective `api.toml` with core defaults for `records`, `frames`,
  `execute`), `user` (the `[user]` table of `api.toml`), `image` (the selected policy or `None`),
  `data` (data files of `[data]` in `session.toml`, by name: `data["board"]`),
  `files` (`{role: {reference, sha256}}` for `target`, `api`, `image`, `session`, `data.<name>`),
  `build` (build manifest summary: `compilers`, `cube_packages`, `libraries`, `defines`, `sources`;
  `None` without a manifest), `case` (`id`,
  `function`, `timeout_s`, `labels`, `contracts`), `stand` (`backend`, `server`, `speed_khz`, `flash`, `reset_command`),
  `gdb` (`version`, `stop_details`, `value_history`, `type_is_signed`).
- `get(path, default=None)` reads a dotted path; a path without a section name reads `target.toml`.
- `origin(path)` reports where a value comes from: `{"state": "file", "file", "sha256"}`,
  `{"state": "default"}`, `{"state": "override", "variable"}` or `{"state": "run", "section"}`;
  a missing path raises `KeyError`.
- `snapshot()` returns a plain JSON-compatible copy of every section; `t.record(name, t.profile)`
  records such a snapshot itself.

Every section and nested mapping is read-only (`TypeError` on assignment); arrays are tuples.
`gdb.stop_details` is `None` until the first stop, then `True` if this GDB reports stop details.
`files[...]["reference"]` does not promise that the path exists on another host.

A data file is declared in `session.toml` and captured with the configuration: the run reads it once,
a package carries it in its capsule, and `origin()` names the file and its SHA-256. TOML is supported;
a name consists of lowercase letters, digits and `_`; a declared but missing file fails before the
MCU is touched.

```toml
# session.toml
[config]
target = "target.toml"
api = "api.toml"

[data]
board = "board.toml"
```

`build.libraries` is joined from the version macros in the sources (`__STM32F4xx_HAL_VERSION_*` →
`{"STM32F4xx_HAL": "1.8.3"}`): these are declared versions, not an API compatibility check.
`build.defines` holds the `-D` keys of the build units and shows whether the firmware uses HAL
(`USE_HAL_DRIVER`) or LL (`USE_FULL_LL_DRIVER`).

## Example

```python
count = t.profile.get("user.measurement.count", 10)
if t.profile.stand["backend"] == "jlink":
    t.check("J-Link reset command", t.profile.stand["reset_command"], "monitor reset")
led = t.profile.data["board"]["board"]["led"]          # "PA5" from board.toml
t.check("CMSIS-only firmware", "USE_HAL_DRIVER" in t.profile.build["defines"], False)
t.record("run", t.profile)
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.4, items 4.14.1–4.14.8.
- [record](record.md), [reset](reset.md).

Since v0.4.0, `stand.backend` also accepts `st-util`; see its [backend configuration](../BACKENDS.md#st-util-v040).
