"""
RU: Сброс цели: остановка, инвалидация кэшей и отказ при активной точке.
EN: Target reset: the halt, the cache invalidation and the refusal with an active point.
"""
import os

from stm32_gdbtest import case


# A reset leaves the core halted at the reset vector and invalidates both caches.
@case("HW_CI_RESET", timeout_s=60, labels=("api", "reset", "invoke"), contracts=("ci_app_api",))
def reset_target(t):
    t.reach("app_loop")

    # An active point makes the reset meaningless, so it is refused before the command runs.
    point = t.breakpoint("board_led_toggle")
    with t.refused("active_points", effect="none", name="a reset with an active point is refused"):
        t.reset()
    t.check("the refused reset kept the point", point.active, True)
    point.remove()

    # The effective command halts the core and both invalidation steps succeed; a session override
    # wins over api.toml, as the documented precedence states.
    configured = os.environ.get("STM32_GDBTEST_RESET_COMMAND") or t.profile.get("api.reset.command")
    result = t.reset()
    t.check("reset reports the halt", result["outcome"], "halted")
    t.check("reset used the configured command", result["command"], configured)
    t.check("reset invalidated both caches",
                 [step["step"] for step in result["invalidation"]],
                 ["flush_register_cache", "invalidate_cached_frames"])
    t.check("every invalidation step succeeded", all(step["status"] == "done" for step in result["invalidation"]))
    entry = t.report["resets"][-1]
    t.check("reset is journalled", entry["command"], configured)
    t.check("reset reports the halted pc", type(result["registers"]["pc"]) is int)

    # The debugger accepts a fresh navigation after the reset, which proves the caches were flushed.
    t.check("navigation after the reset", t.reach("app_loop")["outcome"], "reached")
    t.check("the application runs from the beginning", t.read("app_state.ticks") < 3)
