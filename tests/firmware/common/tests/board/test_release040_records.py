"""
RU: Разнородный журнал 0.4.0: состояние MCU, событие, измерение и копии записей.
EN: Mixed 0.4.0 journal: MCU state, event, measurement and independent record snapshots.
"""
from stm32_gdbtest import case


# Keep typed evidence for capture/export without treating every record as a measurement.
@case("HW_CI_040_RECORDS", timeout_s=45, labels=("api040", "records"), contracts=("ci_app_api",))
def mixed_records(t):
    t.reach("app_loop")
    t.check("journal starts empty", t.records(), [])
    initial = t.read("app_state", fields={"ticks": None, "led": None})
    t.record("state", {"phase": "before", "value": initial})

    # Observe the producer at its caller boundary; no test hooks or injected return values.
    t.reach("app_step")
    t.finish()
    t.finish()
    final = t.read("app_state", fields={"ticks": None, "led": None})
    t.record("transition", {"from": initial["ticks"], "to": final["ticks"], "source": "app_step"})
    t.record("measurement", {"ticks_delta": (final["ticks"] - initial["ticks"]) & 0xFFFFFFFF, "unit": "tick"})
    t.check("one producer increment", t.records("measurement")[0]["data"]["ticks_delta"], 1)

    # Zero, false, null, nested values and a large integer must retain distinct JSON types.
    payload = {"zero": 0, "enabled": False, "missing": None, "large": 2**60 + 1, "text": "evidence"}
    t.record("diagnostic", {"payload": payload, "tags": ["api040", "mixed"]})
    payload["zero"] = 99
    snapshot = t.records("diagnostic")
    snapshot[0]["data"]["tags"].append("local-copy")
    saved = t.records("diagnostic")[0]["data"]
    t.check("input changes do not alter journal", saved["payload"]["zero"], 0)
    t.check("selection changes do not alter journal", saved["tags"], ["api040", "mixed"])
    t.check("sequence spans all record types", [row["sequence"] for row in t.records()], [1, 2, 3, 4])
