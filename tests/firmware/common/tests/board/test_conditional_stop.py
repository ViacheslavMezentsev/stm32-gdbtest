"""
RU: Остановка на N-м вызове: ignore_count, условие, выключение и включение точки.
EN: Stopping at the N-th call: ignore_count, a condition, disabling and enabling the point.
"""
from stm32_gdbtest import case


# Choose the N-th stop with ignore_count and a condition, then disable and enable the point.
@case("HW_CI_CONDITIONAL_STOP", timeout_s=90, labels=("api", "showcase", "breakpoint"), contracts=("ci_app_api",))
def conditional_stop(t):
    t.reach("app_loop")
    start = t.read("app_state.ticks")

    # Two calls are passed over; the third one stops.
    point = t.breakpoint("app_step", ignore_count=2)
    stop = t.resume()["stop"]
    t.check("stopped at the producer", (stop["kind"], stop["function"]), ("breakpoint", "app_step"))
    t.check("the third call stopped", t.read("state->ticks"), start + 2)
    t.check("one stop observed", point.hit_count, 1)

    # A new condition applies to the live point.
    point.condition = f"state->ticks == {start + 5}"
    t.resume()
    t.check("the condition chose the call", t.read("state->ticks"), start + 5)
    t.check("two stops observed", point.hit_count, 2)

    # A disabled point stays but does not stop; its counter is kept.
    point.disable()
    t.check("the point is inactive", point.active, False)
    t.reach("app_loop")
    t.reach("app_loop")
    t.check("no stop while disabled", point.hit_count, 2)

    point.condition = None
    point.enable()
    stop = t.resume()["stop"]
    t.check("enabled again, the point stops", stop["function"], "app_step")
    t.check("the counter continued", point.hit_count, 3)
    point.remove()
