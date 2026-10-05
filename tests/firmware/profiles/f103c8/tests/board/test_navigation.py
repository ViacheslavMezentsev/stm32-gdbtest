"""
RU: Навигация: продолжение, шаг, до места, завершение функции и точка с контекстом.
EN: Navigation: resume, stepping, until, function completion and a point context manager.
"""
from stm32_gdbtest import case


# The receiver copies app_state, calls the producer and publishes the result; four instructions of
# the receiver follow the call, which is what makes a forced return reach a defined place.
CALL_CONSUMED_INSTRUCTIONS = 4


# A point keeps its identity, addresses and observed stops while it is active.
@case("HW_CI_NAVIGATION", timeout_s=60, labels=("api", "navigation"), contracts=("ci_app_api",))
def navigation(target):
    target.reach("app_step")
    baseline = target.read("app_state.ticks")

    # A forced return leaves the producer immediately after the call in the receiver.
    target.ret("42")

    # The receiver consumes the forced value in its next instructions.
    consumed = target.step(CALL_CONSUMED_INSTRUCTIONS, unit="instruction", mode="into")
    target.check("the receiver consumed the forced frame", consumed["outcome"], "completed")
    target.check("the receiver ran every instruction", consumed["completed"],
                 CALL_CONSUMED_INSTRUCTIONS)
    forced_copy = target.read("app_received.produced")
    target.check("the receiver copied the forced value", forced_copy, 42)

    # finish() leaves the receiver and returns into the caller of the receiver.
    finished = target.finish()
    target.check("finish completed", finished["outcome"], "completed")
    target.check("finish left the receiver", finished["function"], "app_loop")
    target.check("finish stop is a function return", finished["stop"]["kind"], "function_return")
    # finish() forces the rest of the frame, so the staged copy on the stack is not published; the
    # application state stays readable and is what the next iteration starts from.
    target.check("the application state stays readable",
                 type(target.read("app_state.ticks")) is int, True)

    # A hardware point reports its state and counts the stops observed for it.
    with target.breakpoint("board_led_toggle") as point:
        target.check("point is active inside the block", point.active, True)
        target.check("point has an address", len(point.addresses) > 0, True)
        stopped = target.resume()
        target.check("resume stopped at the point", stopped["stop"]["kind"], "breakpoint")
        target.check("resume stopped where expected", stopped["stop"]["function"], "board_led_toggle")
        target.check("the point counted the stop", point.hit_count, 1)
    target.check("point is inactive after the block", point.active, False)

    # reach() creates and removes only its own point: a scenario point at the same place stays, and
    # a condition passed to reach() is applied even though a point already exists there.
    with target.breakpoint("board_led_toggle") as kept:
        target.reach("board_led_toggle", condition="1")
        target.check("reach kept the scenario point", kept.active, True)
        target.check("only the scenario point remains", [item.id for item in target.owned
                                                         if item.location == "board_led_toggle"], [kept.id])

    # An instruction step keeps the same point set and reports a step stop.
    target.reach("board_led_toggle")
    stepped = target.step(2, unit="instruction", mode="over")
    target.check("instruction step completed", stepped["outcome"], "completed")
    target.check("instruction step counted both steps", stepped["completed"], 2)
    target.check("instruction step stop is a step", stepped["stop"]["kind"], "step")

    # until() runs to the end of the current line, which must not be a point stop.
    target.reach("board_led_toggle")
    line = target.until()
    target.check("until completed the line", line["outcome"], "completed")
    target.check("until did not stop at a point", line["stop"]["kind"] != "breakpoint", True)

    # reach() reports the destination and the addresses it resolved.
    reached = target.reach("board_adc_sample")
    target.check("reach reports its outcome", reached["outcome"], "reached")
    target.check("reach reports the point", reached["point"] > 0, True)
    target.check("reach resolved addresses", len(reached["addresses"]) > 0, True)
    target.check("reach reports the frame", reached["stop"]["function"], "board_adc_sample")
