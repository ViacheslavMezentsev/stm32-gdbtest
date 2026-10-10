"""
RU: Отказ неверным причинам SKIP 0.4.0 без завершения сценария и изменения журнала.
EN: Refuse invalid 0.4.0 SKIP reasons without ending the scenario or changing its journal.
"""
from stm32_gdbtest import case


# Exercise validation inside GDB, then prove that ordinary target navigation still works.
@case("HW_CI_040_SKIP_VALIDATION", timeout_s=45, labels=("api040", "skip"), contracts=("ci_app_api",))
def skip_validation(t):
    t.record("validation.begin", {"available": True})
    before = t.records()

    # Empty text, whitespace, non-string and invalid Unicode must be refused before control flow changes.
    for reason in ("", " ", None, 7, "\ud800"):
        with t.refused("invalid_arguments", operation="skip", stage="validation", effect="none"):
            t.skip(reason)
    limit = t.profile.get("api.records.max_text_bytes")
    with t.refused("limit_exceeded", operation="skip", stage="validation", effect="none"):
        t.skip("x" * (limit + 1))

    # Refused skips neither consume journal entries nor prevent subsequent execution.
    t.check("journal unchanged after refusal", t.records(), before)
    t.reach("app_loop")
    t.record("validation.complete", {"refused": 6, "function": "app_loop"})
