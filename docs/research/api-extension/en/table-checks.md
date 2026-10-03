# TECH-010: evaluating table usability

[Research](index.md) · [Русский](../ru/table-checks.md)

[TECH-010/011 hardware pairs on F030/F103/F411](techniques-three-boards.md): 7/7 HW and 7/7 prepare each; original checks preserved, restoration PASS. F103 Flash warning retained. Research facades, not core integration.

2026-10-03. The technique is frequently applicable: the [source survey](../results/table-survey.json)
found 47 adjacent blocks of at least 3 checks, totaling 301 checks across 20 CMSIS
scenario files in five profiles. These are structural candidates, not 47 independent
tasks: related board variants are included. HAL and other directories were not scanned.

Conservative eligibility: check with a literal label, value with a literal C expression,
and an integer constant/bitwise arithmetic or value(literal) expectation. Dynamic names,
Python predicates and variable-dependent calculations are excluded. AST analysis does
not establish MMIO read safety.

## Paired comparison

[Explicit tables](../../../../tests/api-extension/table_variants.py) and a
[helper](../../../../tests/api-extension/table_checks.py) preserve original scenarios.
Initial table rows were transferred once from source AST; runtime does not generate
tables or read source files. The independent comparison path executes original functions.

| Scenario | Checks | Dynamic expectations |
| --- | ---: | ---: |
| F030 rtc_init | 13 | 1 |
| F411 adc_init | 16 | 3 |
| F103 timer_init | 8 | 1 |

[Paired tests](../../../../tests/api-extension/test_table_checks.py): 3 successful runs,
37 failures at each check and 42 failures at each read, including expected expressions.
82 paired cases compare full reach/value/check traces and exception names/types.
Two further tests cover empty tables and no premature expected-expression evaluation.
Check failures are injected into the model: this tests Python sequencing, not MCU/registers.

Windows regression: 84 tests, 83 PASS/1 CMake skip. No new hardware runs.
Linux Docker: 84/84 PASS; CI documentation: 4/4 PASS.
Original settings are preserved: F030 PRER uses 311 and RTC vector 18;
the user's F4 example values were not copied onto F030.

## Conclusion

Recommended as [TECH-010](../../../en/TESTING_TECHNIQUES.md#tech-010), a consumer helper
over existing value/check, outside the API package. It separates data from execution
and makes register reviews consistent. Neither check count nor GDB calls decrease;
table formatting may increase line count. No execution speedup is claimed.

Prefer ordinary tuples and for, without side-effect comprehensions, map or all:
check does not return an aggregate boolean. String expectations mean C expressions,
appropriate to current integer-returning value, not a convention for future typed strings.

Only adjacent checks in one context belong together. Keep reach, injections, event
waits, Python state changes and dependent calculations between separate tables.
Only harmless constants/calculations belong in table construction; putting value calls
inside rows would read MCU state prematurely.

Next adaptation step: apply tables to static blocks in paired first-package scenarios.
MCU acceptance requires real runs on an agreed stand, preserving preflight, context,
baseline/restore and case/contracts identifiers. Production scenarios and core unchanged.
