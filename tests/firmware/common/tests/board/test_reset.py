"""
RU: Сброс цели: остановка, инвалидация кэшей и отказ при активной точке.
EN: Target reset: the halt, the cache invalidation and the refusal with an active point.
"""
import os

from stm32_gdbtest import case, ApiError, case


# A reset leaves the core halted at the reset vector and invalidates both caches.
@case("HW_CI_RESET", timeout_s=60, labels=("api", "reset", "invoke"), contracts=("ci_app_api",))
def reset_target(target):
    target.reach("app_loop")

    # An active point makes the reset meaningless, so it is refused before the command runs.
    point = target.breakpoint("board_led_toggle")
    try:
        target.reset()
    except ApiError as error:
        target.check("active point code", error.details["code"], "active_points")
        target.check("active point effect", error.details["effect"], "none")
    else:
        target.check("a reset with an active point must be refused", False, True)
    target.check("the refused reset kept the point", point.active, True)
    point.remove()

    # The effective command halts the core and both invalidation steps succeed; a session override
    # wins over api.toml, as the documented precedence states.
    configured = os.environ.get("STM32_GDBTEST_RESET_COMMAND") or target.profile.get("api.reset.command")
    result = target.reset()
    target.check("reset reports the halt", result["outcome"], "halted")
    target.check("reset used the configured command", result["command"], configured)
    target.check("reset invalidated both caches",
                 [step["step"] for step in result["invalidation"]],
                 ["flush_register_cache", "invalidate_cached_frames"])
    target.check("every invalidation step succeeded",
                 all(step["status"] == "done" for step in result["invalidation"]), True)
    entry = target.report["resets"][-1]
    target.check("reset is journalled", entry["command"], configured)
    target.check("reset reports the halted pc", type(result["registers"]["pc"]) is int, True)

    # The debugger accepts a fresh navigation after the reset, which proves the caches were flushed.
    target.check("navigation after the reset", target.reach("app_loop")["outcome"], "reached")
    target.check("the application runs from the beginning",
                 target.read("app_state.ticks") < 3, True)
