"""
RU: Условный SKIP 0.4.0 по конфигурации с сохранением причины и выполнением finally.
EN: Configuration-driven 0.4.0 SKIP preserves its reason and executes finally.
"""
from stm32_gdbtest import case


# Configuration decides applicability; a hardware failure must never become a skip.
@case("HW_CI_040_SKIP", timeout_s=45, labels=("api040", "skip"), contracts=("ci_app_api",))
def optional_loop(t):
    enabled = t.profile.user.get("release040", {}).get("optional_loop", True)
    t.check("applicability is a boolean", type(enabled) is bool)
    t.record("capability", {"name": "optional_loop", "available": enabled, "source": "api.toml"})

    # SKIP terminates this scenario only; finally still contributes evidence to capture.
    try:
        if not t.records("capability")[-1]["data"]["available"]:
            t.skip("optional_loop disabled by session configuration")
        t.reach("app_loop")
        t.record("optional.executed", {"function": "app_loop"})
    finally:
        t.record("optional.finally", {"visited": True})

    # This record must be absent from a skipped run and present from an enabled run.
    t.record("optional.completed", {"visited": True})
