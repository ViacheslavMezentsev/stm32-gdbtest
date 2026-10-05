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
def navigation(t):
    t.reach("app_step")
    baseline = t.read("app_state.ticks")

    # A forced return leaves the producer immediately after the call in the receiver.
    t.ret("42")

    # The receiver consumes the forced value in its next instructions.
    consumed = t.step(CALL_CONSUMED_INSTRUCTIONS, unit="instruction", mode="into")
    t.check("the receiver consumed the forced frame", consumed["outcome"], "completed")
    t.check("the receiver ran every instruction", consumed["completed"], CALL_CONSUMED_INSTRUCTIONS)
    forced_copy = t.read("app_received.produced")
    t.check("the receiver copied the forced value", forced_copy, 42)

    # finish() leaves the receiver and returns into the caller of the receiver.
    finished = t.finish()
    t.check("finish completed", finished["outcome"], "completed")
    t.check("finish left the receiver", finished["function"], "app_loop")
    t.check("finish stop is a function return", finished["stop"]["kind"], "function_return")
    t.check("the receiver returns nothing", finished["return_state"], "void")

    # finish() forces the rest of the frame, so the staged copy on the stack is not published; the
    # application state stays readable and is what the next iteration starts from.
    t.check("the application state stays readable", type(t.read("app_state.ticks")) is int)

    # A hardware point reports its state and counts the stops observed for it.
    with t.breakpoint("board_led_toggle") as point:
        t.check("point is active inside the block", point.active)
        t.check("point has an address", len(point.addresses) > 0)
        stopped = t.resume()
        t.check("resume stopped at the point", stopped["stop"]["kind"], "breakpoint")
        t.check("resume stopped where expected", stopped["stop"]["function"], "board_led_toggle")
        t.check("the point counted the stop", point.hit_count, 1)
    t.check("point is inactive after the block", point.active, False)

    # finish() reports the value the producer returned: GDB keeps it in the value history.
    t.reach("app_step")
    ticks = t.read("state->ticks")
    produced = t.finish()
    t.check("finish left the producer", produced["returned_from"], "app_step")
    t.check("finish returned into the receiver", produced["function"], "app_receiver_step")
    t.check("the returned value is available", produced["return_state"], "available")
    t.check("finish returned the incremented count", produced["return_value"], ticks + 1)

    # reach() creates and removes only its own point: a scenario point at the same place stays, and
    # a condition passed to reach() is applied even though a point already exists there.
    with t.breakpoint("board_led_toggle") as kept:
        t.reach("board_led_toggle", condition="1")
        t.check("reach kept the scenario point", kept.active, True)
        t.check("only the scenario point remains", [item.id for item in t.owned
                                                    if item.location == "board_led_toggle"], [kept.id])

    # An instruction step keeps the same point set and reports a step stop.
    t.reach("board_led_toggle")
    stepped = t.step(2, unit="instruction", mode="over")
    t.check("instruction step completed", stepped["outcome"], "completed")
    t.check("instruction step counted both steps", stepped["completed"], 2)
    t.check("instruction step stop is a step", stepped["stop"]["kind"], "step")

    # until() runs to the end of the current line, which must not be a point stop.
    t.reach("board_led_toggle")
    line = t.until()
    t.check("until completed the line", line["outcome"], "completed")
    t.check("until did not stop at a point", line["stop"]["kind"] != "breakpoint")

    # reach() reports the destination and the addresses it resolved.
    reached = t.reach("board_adc_sample")
    t.check("reach reports its outcome", reached["outcome"], "reached")
    t.check("reach reports the point", reached["point"] > 0)
    t.check("reach resolved addresses", len(reached["addresses"]) > 0)
    t.check("reach reports the frame", reached["stop"]["function"], "board_adc_sample")
