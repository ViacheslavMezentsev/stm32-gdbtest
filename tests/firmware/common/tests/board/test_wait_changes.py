"""
RU: Ожидание через watchpoint с бюджетом событий и явной обработкой других остановок.
EN: Watchpoint wait with an event budget and explicit unrelated-stop handling.
"""
from stm32_gdbtest import case


# A stop budget bounds repeated events; the runner timeout bounds an unreturned resume.
def wait_changes(t, path, predicate, *, max_stops):
    if type(max_stops) is not int or max_stops < 1:
        raise ValueError("max_stops must be a positive integer")
    with t.watch(path) as point:
        # Every resume must stop at our point before the predicate is evaluated.
        for attempt in range(max_stops):
            stop = t.resume()["stop"]
            actual = t.read(path)
            ids = stop.get("watch", []) + stop.get("breakpoints", [])
            owned = stop["kind"] == "watchpoint" and point.id in ids
            t.record("wait.observation", {"attempt": attempt, "point": point.id, "stop": stop,
                                          "actual": actual, "frames": t.frames(4)["frames"]})
            if not owned:
                return {"outcome": "unexpected-stop", "stop": stop, "actual": actual}
            if predicate(actual):
                return {"outcome": "matched", "stop": stop, "actual": actual}
        return {"outcome": "exhausted", "actual": actual}


# Exercise normal completion, an unrelated stop, budget exhaustion and predicate failure.
@case("HW_CI_WAIT_CHANGES", timeout_s=60, contracts=("ci_app_api",))
def watch_wait(t):
    t.reach("app_loop")
    guards = [point for point in t.owned if point.active]
    before = t.read("app_state.ticks")
    result = wait_changes(t, "app_state.ticks", lambda value: ((value - before) & 0xffffffff) >= 2, max_stops=3)
    t.record("wait.result", dict(result, mode="normal"))
    t.check("two changes matched", result["outcome"], "matched")
    t.check("exactly two increments", (result["actual"] - before) & 0xffffffff, 2)
    t.check("normal cleanup", any(p.watch and p.active for p in t.owned), False)

    # The foreign breakpoint must remain alive when the helper declines the stop.
    t.reach("app_loop")
    with t.breakpoint("app_receiver_step") as foreign:
        result = wait_changes(t, "app_state.ticks", lambda value: True, max_stops=2)
        t.record("wait.result", dict(result, mode="foreign"))
        t.check("unrelated stop is not consumed", result["outcome"], "unexpected-stop")
        t.check("foreign breakpoint preserved", foreign.active)
        t.check("foreign cleanup", any(p.watch and p.active for p in t.owned), False)

    # An event budget ends politely even when the condition cannot be satisfied.
    t.reach("app_loop")
    result = wait_changes(t, "app_state.ticks", lambda value: False, max_stops=2)
    t.record("wait.result", dict(result, mode="budget"))
    t.check("event budget exhausted", result["outcome"], "exhausted")
    t.check("budget cleanup", any(p.watch and p.active for p in t.owned), False)

    # Python exceptions propagate while with still removes the helper's watchpoint.
    def invalid(value):
        raise ValueError("predicate failure")

    t.reach("app_loop")
    caught = False
    try:
        wait_changes(t, "app_state.ticks", invalid, max_stops=1)
    except ValueError as error:
        caught = str(error) == "predicate failure"
    t.check("predicate error propagated", caught)
    t.check("exception cleanup", any(p.watch and p.active for p in t.owned), False)
    t.check("original guards preserved", all(point.active for point in guards))
    t.record("wait.cleanup", {"predicate_error": caught, "guards_active": all(p.active for p in guards)})

