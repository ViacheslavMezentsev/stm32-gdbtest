# RecordError: structured rejection

[Research](index.md) · [Русский](../ru/record-errors.md)

2026-10-03. Implemented API spec 0.2.0 clauses 5.3–5.4 diagnostics in isolated
[evidence.py](../../../../tests/api-extension/evidence.py). Core unchanged.
This implements the previously accepted Q18 contract without changing requirements.

## Contract and checks

| code | Cause / verification |
| --- | --- |
| invalid_name | Empty name, wrong type or str subclass; invalid records filter |
| unsupported_type | Unsupported objects, bytes/tuple, subclasses, non-string keys |
| invalid_text | Lone surrogate in a name, key or value |
| non_finite | NaN and positive/negative infinity |
| cycle | Cyclic list; existing shared non-cyclic reference check preserved |
| limit_exceeded | limit=records/nodes/depth/text_bytes/integer_bits |

The prototype uses limit=None for other errors. The public class retains ValueError
as its base; production import location and base class remain API spec question 10.2.5.
Messages and precedence when multiple constraints fail are not contractual.

[New tests](../../../../tests/api-extension/test_record_errors.py) verify:

- Every code and limit, including both text overflow paths (characters and UTF-8 bytes).
- Existing entries survive rejection; the next entry receives the next sequence.
- Rejection consumes no node/text budget; subsequent valid writes fill exact budgets.
- Explicit recovery can record diagnostics and continue after catching the exception.
- Injected MemoryError escapes copying as the same exception object; the journal survives.

This is not exhaustive allocator fault injection. Agent classification of unhandled
exceptions as ERROR and check mismatches as FAIL remains unchanged; integration
verification is pending separate core-promotion approval.

## Results and reproduction

- Windows: 73 research tests, 72 PASS / 1 CMake skip because no compiler is in PATH.
- Linux Docker: 73/73 PASS; CI documentation: 4/4 PASS.
- GDB14/Python 3.11.4 and GDB16/Python 3.13.12: 18/18 PASS each, no skips, ELF or MCU.
- [GDB14 JSON](../results/record-errors-gdb14.json), [GDB16 JSON](../results/record-errors-gdb16.json): versions, prototype hash, full test log.

Host: `python -B -m unittest discover -s tests/api-extension -q`.
In GDB from the repository root: `python import sys; sys.path.insert(0, 'tests/api-extension'); import run_record_errors; run_record_errors.run('<result.json>')`.
Use `-nx -batch -q -iex "set auto-load off"` and supply the Python command through `-ex`.

The previous M5 report and specification appendix F describe the prototype at M5.
This evidence completes its code/limit work, not production integration. Q6/Q19
measurements retain the earlier prototype hash and were not overwritten.
Numeric bounds remain a proposal awaiting approval.

Next: verify legacy config/config_props for JSON and old packages in the research
facade, then consolidate remaining integration prerequisites.
