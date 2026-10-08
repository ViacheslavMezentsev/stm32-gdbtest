# skip

[API](index.md) · [Русский](../../ru/api/skip.md)

`skip(reason) -> NoReturn`

Available: Unreleased after0.3.0; API specification0.3.9; API_VERSION=1.

Ends an inapplicable scenario with SKIP. reason must be an exact nonblank str containing valid
Unicode; UTF-8 size must not exceed api.records.max_text_bytes. Excess raises ApiError
limit_exceeded; invalid input raises invalid_arguments. Does not consume the records budget.

```python
target.record("capability", {"available": False})
if not target.records("capability")[-1]["data"]["available"]:
    target.skip("Optional interface is not configured")
```

records hold arbitrary per-scenario data. skip does not disable other scenarios; use if to omit
a block. If testing interface health, communication failure is FAIL/ERROR. Unknown is not SKIP.

With capture enabled, retain records with completion=interrupted. JSON skip_reason and JUnit
skipped/message carry the reason. Exit77, CTest SKIP_RETURN_CODE=77; SKIP is not PASS.
Capture errors retain scenario SKIP but yield command code2 and infrastructure error.
Teardown errors change status to ERROR while retaining skip_reason.

The method never returns: internal control flow inherits BaseException; except Exception does
not catch it and finally still runs. Do not catch BaseException. Caught skip followed by normal
scenario return yields ERROR. Recorded failed checks and active exceptions cannot become SKIP.
Arbitrary previously caught errors are not tracked. No automatic restriction after reads or
navigation; agent may already have programmed/booted MCU. No rollback. Do not use skip in finally
to replace an error.

Migration: consumers must accept77 separately from0/1/2; never use max for severity.
Old reports remain readable. `run_hw.py --allow-skip HW_ID` permits a particular skip; unexpected
SKIP is rejected by default. skipped/passed counters remain separate; all SKIP means nothing_tested.
requires is unsupported. No published release includes this method yet.

Tests: [host](../../../tests/host/test_skip.py); [API_ACCEPTANCE](../API_ACCEPTANCE.md).
