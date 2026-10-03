# E1: paired scenario comparison

[Research](index.md) · [Русский](../ru/e1-comparison.md)

2026-10-03. [Variants](../../../../tests/api-extension/scenario_variants.py),
[tests](../../../../tests/api-extension/test_scenario_variants.py),
[results and hashes](../results/e1-paired.json).
Original functions are imported from current scenarios, not copied into a test oracle.

## Equivalence checks

Windows host: 22/22 tests overall. Three new tests cover 22 paired inputs:
16 CMSIS/HAL ADC cases (normal, boundaries, invalid quality, out-of-range values),
2 read failures and 4 HAL blink cases (normal, tick wrap, short interval, wrong LED).
Complete reach/value/check sequences, exceptions and recorded values are compared.
Blink evidence remains available after the subsequent interval assertion fails.
HAL is checked on the host only here.

Hardware: same Windows/F411CE/ST-Link/OpenOCD HLA/GDB14 and ELF as the
[first experiment](e1.md). Original HW_CI_ADC_UNITS and HW_E1_ADC_PAIR ran
sequentially with reset. All 9 checks matched (6 navigation and 3 scenario checks).
Both VDDA readings were 3302 mV; original temperature was 27668 m°C, variant 27035 m°C.
Physical readings need not match between runs. Matching expectations and evidence
structure were checked, not deterministic analog observations.
Preparation 4/4 PASS, hardware baseline/variant/restore 4/4 PASS.
HAL restored; HW_BOOT/HW_GPIO and reset_run confirmed.

## Benefit and cost

| Scenario | AST statements before → after | report accesses before → after |
| --- | --- | --- |
| CMSIS ADC units | 6 → 6 | 1 → 0 |
| HAL ADC units | 9 → 9 | 1 → 0 |
| HAL blink | 10 → 10 | 1 → 0 |

Counts include nested ast.stmt nodes inside the function, excluding its definition.
The facade, journal implementation and research report transport are outside this
metric: they add code rather than providing a free reduction of the whole system.
Only evidence writes change in the variants; original checks remain intact.

Single measurements do not become shorter. Repeated observations lose manual
setdefault/append plumbing and gain snapshots, common ordering, Python queries
and statistics. Costs include copying and bounded journal memory. Direct report
access remains only in the hardware harness to preserve evidence; no export API
is proposed. Scenarios should not replace ordinary locals with journal queries
without a reason.

E1 is complete within the selected scope: runtime contract, queries, statistics,
host failures, real GDB/F411 and paired comparison. Core integration is not approved.
HAL on F030, memory/time cost measurements and retention after process crashes
remain limitations/debt; an in-memory journal does not promise crash durability.
Next is E2: bounded array and selected-field reads, starting with a contract and
host prototype, then comparison with individual value calls.
