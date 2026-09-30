# ELF/HAL contracts

[Documentation](index.md) → Contracts · [Русский](../ru/CONTRACTS.md)

A scenario declares contract names literally in `@case(..., contracts=("name",))`.
Definitions live in `tests/contracts.json` of the profile directory. Contracts that
are not requested give `NOT_REQUESTED` in the report — this is not evidence of
compatibility and not a SKIP result.

## Order and responsibilities

1. The runner copies the ELF and checks the build manifest.
2. Only the requested contracts are loaded. An unknown name or schema is ERROR. For
   `source_reviews` the hashes are compared with the inputs of the verified manifest.
3. The selected declarations, the registry SHA-256 and `contract-request.json` are saved.
4. A separate batch GDB runs with this ELF, auto-load disabled, without a server and
   without connecting to the target; the external limit is 15 s. Checks use only
   Symbol/Type/Block and `list`, `info macro`, `macro expand`, `whatis` — no `parse_and_eval`,
   no target function calls, no memory writes.
5. `contract-result.json` is accepted only with PASS, exit code 0 and a matching ELF
   SHA-256. An error, a missing result or a timeout stops the run before the GDB server.
6. After a successful preflight the hardware scenario runs with the usual identity,
   Flash, reset, breakpoint and finish checks. Preflight results are part of
   `result.json` and JUnit; the log is `contract-preflight.log`.

`run --prepare-only` performs steps 1–5 without hardware; the CMake test
`prepare.<ID>` does the same in the offline CTest set.

The mechanism is [contracts.py](../../stm32_gdbtest/contracts.py); MCU and HAL
expectations live in the profile, scenarios in the consumer. Changing a contract does
not require rebuilding the firmware: it is a test expectation, and its selected
snapshot is stored separately from the build.

## What schema 1 defines

- `functions`: global functions, return type and an **ordered list** of arguments
  (`name`, `type`). Argument count and type order, argument names and their types in
  the block are checked.
- `type_context`: a function from `functions` whose block resolves `fields` and `enums`.
- `fields`: required structure fields and their types; extra fields are allowed.
- `enums`: required enum constants and values; extra values are allowed.
- `macros`: `context` (a function) and `expressions` — see [HAL macros](HAL_MACRO_GUIDE.md).
  Each expression is checked for its definition, expansion and the type of the expansion
  (`whatis` on the expansion text, no memory reads; a command-line macro `-DNAME` also counts
  as defined). If the expansion refers to a type missing from the debug info
  (`(DBGMCU_TypeDef *)…` when the firmware does not use DBGMCU), the contract reports ERROR
  before the server; a build with `-fno-eliminate-unused-debug-types` helps. Statement macros
  (`do { } while (0)`) are not expressions: the report has `type_note` for them, not an error.
- `source_reviews`: file, SHA-256 and the `reason` of a manual review of the used behaviour.

Argument and return types are resolved in the function's own block. A global
`lookup_type` produced a false `GPIO_TypeDef` mismatch between C and C++ compilation
units, and comparing strings does not fix that, so GDB Type equality in the right
context is used. Named types, `const Type` and `Type *` are supported; there is no
universal C/C++ parser for arrays, templates and function pointers.

## Limits of the evidence

- Before a NULL injection study the used HAL source and pin its hash in
  `source_reviews`. Never update the hash mechanically to get a PASS.
- A matching signature does not prove the semantics of the body, transitive headers
  or effective macros.
- `force_return` skips the function body: such a test checks the caller's reaction.
- A callback signature does not prove the IRQ route; a DWARF argument does not prove
  the value is available at halt. Optimized-out values and pending breakpoints are
  checked at run time.
- The preflight expands but does not evaluate macro expressions. `source_reviews`
  rely on the [build manifest](MANIFESTS.md).

CI exercises the mechanism on the CI firmware, including 10 negative contract
variants ([checks and CI](testing.md)).
[Profile contracts and offline regression](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/HAL_CONTRACTS.md)
(Russian) stay with the stand project.
