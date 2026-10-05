"""
RU: Остановка на N-м вызове: ignore_count, условие, выключение и включение точки.
EN: Stopping at the N-th call: ignore_count, a condition, disabling and enabling the point.
"""
from stm32_gdbtest import case


@case("HW_CI_CONDITIONAL_STOP", timeout_s=90, labels=("api", "showcase", "breakpoint"), contracts=("ci_app_api",))
def conditional_stop(target):
    target.reach("app_loop")
    start = target.read("app_state.ticks")

    # Two calls are passed over; the third one stops.
    point = target.breakpoint("app_step", ignore_count=2)
    stop = target.resume()["stop"]
    target.check("stopped at the producer", (stop["kind"], stop["function"]), ("breakpoint", "app_step"))
    target.check("the third call stopped", target.read("state->ticks"), start + 2)
    target.check("one stop observed", point.hit_count, 1)

    # A new condition applies to the live point.
    point.condition = f"state->ticks == {start + 5}"
    target.resume()
    target.check("the condition chose the call", target.read("state->ticks"), start + 5)
    target.check("two stops observed", point.hit_count, 2)

    # A disabled point stays but does not stop; its counter is kept.
    point.disable()
    target.check("the point is inactive", point.active, False)
    target.reach("app_loop")
    target.reach("app_loop")
    target.check("no stop while disabled", point.hit_count, 2)

    point.condition = None
    point.enable()
    stop = target.resume()["stop"]
    target.check("enabled again, the point stops", stop["function"], "app_step")
    target.check("the counter continued", point.hit_count, 3)
    point.remove()
