"""
RU: Получатель возвращаемого значения: принудительный возврат из app_step доходит до вызывающего.
EN: Receiver of a returned value: a forced return from app_step reaches the caller.
"""
from stm32_gdbtest import case


# Read the receiver's observed state; the application publishes it, not the test.
def _receiver(t):
    return {"produced": t.read("app_received.produced"),
            "calls": t.read("app_received.calls")}


# The firmware calls the producer through app_receiver_step; the caller consumes the returned value.
@case("HW_CI_RET_RECEIVER", labels=("api", "ret"), contracts=("ci_app_api",))
def ret_receiver(t):
    t.reach("app_step")
    initial = _receiver(t)

    # The caller copies the application state before the call; a forced value must replace that copy
    # in the receiver's own object once its body completes.
    t.write("app_state.ticks", 7)
    t.ret("42")
    t.reach("app_step")
    after_value = _receiver(t)
    t.check("forced value reached the receiver", after_value["produced"], 42)
    t.check("receiver did not keep the caller copy", after_value["produced"] != 7)
    t.check("receiver counted the call", after_value["calls"] > initial["calls"])

    # A forced zero must reach the receiver as well.
    t.write("app_state.ticks", 9)
    t.ret("0")
    t.reach("app_step")
    after_zero = _receiver(t)
    t.check("forced zero reached the receiver", after_zero["produced"], 0)
    t.check("receiver counted the second call", after_zero["calls"] > after_value["calls"])
