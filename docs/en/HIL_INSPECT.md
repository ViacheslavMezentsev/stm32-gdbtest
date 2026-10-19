# Inspect HIL links without execution

[Documentation](index.md) · [Русский](../ru/HIL_INSPECT.md)

`inspect` validates selected configuration and displays HIL, backend and SVD links.
It never runs CMake, GDB, servers, emulators or scenarios, and never connects to a board
or network. Scenario metadata is collected through AST without importing Python.
Success means structural validity, not scenario PASS or board qualification.

```powershell
# Actual configuration of an existing build
python -m stm32_gdbtest inspect --session build/debug/hwtest/session.json

# Compact layout before building
python -m stm32_gdbtest inspect --config hil/F103CB/session.toml --profile-dir hil/common --project-root .

# Distributed layout, additional scenarios and machine-readable output
python -m stm32_gdbtest inspect --config hil/sessions/f411.toml --profile-dir hil --test-dir hil/extra/tests --format json --output hil-inspect.json
```

`--session` and `--config` are mutually exclusive. Session mode uses scenario roots
from JSON and rejects `--profile-dir`/`--test-dir`. Config mode requires `--profile-dir`:
its tests/ (or legacy Tests/) contains board/test_*.py. Repeat `--test-dir` for an
additional root containing board/ and requirements.md. Discovery is nonrecursive;
duplicate canonical roots and IDs are errors. Both layouts are supported without a new registry.

Stand selection matches the runner: CLI `--stand` → STM32_GDBTEST_STAND → session.stand.
No selection produces WARN stand.not_selected. Finding an executable does not prove
it works. OpenOCD scripts and remote tools are DEFERRED to their server resolver.
Renode validates a self-contained REPL; QEMU validates the supported machine schema.
No `--version`, SSH or automatic stand selection is performed.

## Paths and captured configuration

CLI paths are relative to cwd. TOML config/data and mmio.svd are relative to their
session.toml. Relative runtime JSON fields retain their cwd dependency; the JSON folder
is not their base. `--project-root` only controls report presentation. Executables use
normal PATH/expand_path rules; Renode platform uses the stand directory. Not every
TOML field supports variable expansion. External links are allowed; junctions/symlinks
show original and canonical paths. Existing runner path rules remain unchanged.

For `_config_capsule`, captured bytes and hashes are validated without reopening original
TOML/SVD files. Scenarios and ELF remain filesystem references. Legacy runtime without
session and ZIP input are unsupported; an extracted runtime session can be inspected.
SVD uses the bounded parser, including access/effect semantics and prohibited XML forms.
FOUND does not imply VALID. Configuration without MMIO does not require SVD. SVD validity
does not prove correspondence with physical hardware. contracts.json is checked as JSON,
without ELF preflight; ELF is only checked for existence.

## Output and JSON schema 1

`--format text|json` defaults to text; stdout unless `--output` is provided. The output
parent directory must exist. External absolute paths become `<external>`;
`--local-details` shows local paths. Key contents, stand serial/hostname, raw TOML and
exception text are never emitted. Filenames within the project remain visible.

| Field | Content |
|---|---|
| schema, scope, runtime_checked | 1, structure, false |
| selection | mode=config/session, source=disk/capsule, stand=none/cli/env/session |
| nodes | id, role, path, resolved_path, origin, status, sha256 |
| edges | source, target, field, base_kind, resolver, status |
| scenarios | id, function, path, labels, contracts, timeout_s |
| svd | source, availability, semantics, registers |
| diagnostics | code, severity, node, field, message |
| summary | ERROR/WARN/DEFERRED counts |
| configuration_valid | true only when there are no ERROR diagnostics |
| backend | present after successful stand validation |

Node/edge status is FOUND/MISSING/DEFERRED. Origin identifies disk/capsule/ast or an
external resolver. Paths and sha256 may be null; executable, SSH and ELF are not hashed.
Configuration hashes describe validated snapshots; capsule paths are null.
SVD availability: NOT_CONFIGURED/FOUND/MISSING; semantics: NOT_CHECKED/VALID/INVALID;
registers is a count or null. Invalid snapshots can leave incomplete information.
An ERROR can leave a partial graph; further validation is not guaranteed.

Stable diagnostic codes (message is a readable code representation, not a parsing interface):

- input.conflict/profile_required; file.missing;
- runtime.invalid/legacy_unsupported/cwd_dependent (the latter WARN);
- config.source/session/reference/target/image/data/api_schema/api_parameter/conflict/stale_selection/transport/invalid;
- configuration.invalid; svd.source/integrity/invalid;
- scenarios.directory_missing/duplicate_root/invalid; requirements.invalid;
- backend.invalid/environment_mismatch; stand.not_selected (WARN).

Exit 0: no ERROR. Exit 2: ERROR, or WARN with `--warnings-as-errors`.
DEFERRED alone is not promoted to an error. Output failure prints
`ERROR: output.unwritable` to stderr and exits 2; argument errors also exit 2.

Added in 0.5.0 without changing Target API. Complements `doctor` and `run --prepare-only`,
which perform different checks and may execute tools.
