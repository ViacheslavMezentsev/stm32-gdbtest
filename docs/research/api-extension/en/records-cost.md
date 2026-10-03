# Q6/Q19: runtime journal costs

[Research](index.md) · [Русский](../ru/records-cost.md)

Owner decision 2026-10-03: numeric bounds/cost criterion and public RecordError import accepted. Q6/Q19 and API spec questions 10.2.4–10.2.5 closed; API spec 0.2.1, system spec 0.61. Upper-bound implementation and core integration are pending; integration approval remains separate.

2026-10-03. Measured the unchanged evidence.Journal prototype; core and specifications
unchanged. This proposes numeric limits; it neither approves them nor accepts a future Target.

## Method

The [script](../../../../tests/api-extension/measure_records.py) runs in CPython and
GDB Python without ELF, server or MCU. Windows x64 environments: CPython 3.11.9;
GDB 14.2.90.20240526-git / Python 3.11.4 from xPack 13.3.1-1.1;
GDB 16.3.90.20250906-git / Python 3.13.12 from xPack 15.2.1-1.1.

13 input shapes cover measurements, node/text/depth/int boundaries, Unicode,
dicts and increased budgets. After warmup, 9 batches of 10 operations with GC enabled.
Write time includes journal creation, population and disposal; reads include result
disposal. Medians summarize batch means, not individual calls. JSON retains every
batch; maximum batch mean is not worst-case latency.

Separate tracemalloc runs use preallocated input: retained/peak measure new allocations.
graph_bytes measures reachable Python objects with identities deduplicated, including
immutable input values. Neither is RSS. Strings/ints are not physically duplicated;
sharing immutable values is safe while containers remain detached.

## Results

All 13 cases and 5 boundary checks passed in each environment. Exact node/text/depth/
integer boundaries are accepted and excess rejected; rejected writes leave an empty
journal and the next entry receives sequence=1. The 129th record is rejected while
preserving the first 128.

| Input | Write GDB14 / GDB16, us | Read GDB14 / GDB16, us | Journal objects GDB14, bytes |
| --- | ---: | ---: | ---: |
| 10 VDDA/temperature pairs | 18.7 / 14.9 | 7.2 / 5.0 | 5107 |
| 128 pairs | 245.0 / 202.1 | 91.2 / 64.3 | 52703 |
| List, 4096 nodes | 818.0 / 534.1 | 217.7 / 182.4 | 148661 |
| Dict, 4096 nodes | 1053.6 / 794.1 | 160.3 / 155.6 | 217674 |
| Text, 65536-byte budget | 3.1 / 2.6 | 0.7 / 0.4 | 66705 |
| 1024 pairs | 2218.6 / 1667.7 | 731.5 / 516.4 | 415295 |
| List, 32768 nodes | 6440.5 / 4366.0 | 1686.4 / 1448.7 | 1195765 |

Ten retained reads of 128 pairs peak at about 0.48 MB of new allocations; 1024 pairs
at 3.86 MB. A small journal does not limit consumer-held copies. Unicode UTF-8 encoding
costs about 18 us versus 3 us for ASCII with a similar text budget in GDB14, illustrating
input-shape effects.

Raw results: [CPython](../results/records-cost-host.json),
[GDB14](../results/records-cost-gdb14.json), [GDB16](../results/records-cost-gdb16.json).
JSON includes prototype source SHA256, versions, batches and memory, without personal paths.

## Recommendation for approval

Retain moderate prototype defaults; allow api.toml increases within an initial limit profile:

| records parameter | Default | Proposed maximum |
| --- | ---: | ---: |
| max_records | 128 | 1024 |
| max_nodes | 4096 | 32768 |
| max_text_bytes | 65536 | 524288 |
| max_depth | 8 | 32 |
| max_integer_bits | 256 | 1024 |

All are positive integers excluding bool. Limits apply together: 1024 records are not
guaranteed when nodes/text run out first. Increased values were tested with individual
shapes, not as proof of maximum cost for all combinations. This conservative initial
profile can expand with evidence. The loader does not enforce these upper bounds yet;
implementation follows approval.

For integration acceptance, repeat the suite in target GDB builds and investigate median
regressions exceeding 2x this baseline in comparable environments. This is a review
threshold, not an API time guarantee. Full resource guarantees need further requirements,
including RSS and consumer-held copy limits.

Scenario practice: read once and reuse the local result; use records('name') before
Python filtering. records()[:3] copies the full journal first. MCU sampling has separate
scenario-budget costs: this experiment measures Python operations, not ADC or GDB memory reads.

## Status and next step

Q6/Q19 remain open pending owner approval of limits and criteria. Windows research
regression: 68 tests, 67 PASS and 1 CMake skip (no compiler in PATH); Linux Docker
68/68 PASS, docs 4/4 PASS. Next: agree on
limits, then verify structured RecordError diagnostics in the isolated prototype.
Core integration remains a separate decision.

Repeat from the repository root: `python -B tests/api-extension/measure_records.py <output.json>`.
For GDB, run `python import sys; sys.path.insert(0, 'tests/api-extension'); import measure_records; measure_records.run('<output.json>')`
through `-ex` after `gdb -nx -batch -q -iex "set auto-load off"`.
