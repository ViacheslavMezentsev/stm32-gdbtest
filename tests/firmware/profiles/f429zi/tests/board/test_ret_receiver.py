"""
RU: Получатель возвращаемого значения: принудительный возврат из app_step доходит до вызывающего.
EN: Receiver of a returned value: a forced return from app_step reaches the caller.
"""
from stm32_gdbtest import case


# Read the receiver's observed state; the application publishes it, not the test.
def _receiver(target):
    return {"produced": target.read("app_received.produced"),
            "calls": target.read("app_received.calls")}


# The firmware calls the producer through app_receiver_step; the caller consumes the returned value.
@case("HW_CI_RET_RECEIVER", labels=("api", "ret"), contracts=("ci_app_api",))
def ret_receiver(target):
    target.reach("app_step")
    initial = _receiver(target)

    # The caller copies the application state before the call; a forced value must replace that copy
    # in the receiver's own object once its body completes.
    target.write("app_state.ticks", 7)
    target.ret("42")
    target.reach("app_step")
    after_value = _receiver(target)
    target.check("forced value reached the receiver", after_value["produced"], 42)
    target.check("receiver did not keep the caller copy", after_value["produced"] != 7, True)
    target.check("receiver counted the call", after_value["calls"] > initial["calls"], True)

    # A forced zero must reach the receiver as well.
    target.write("app_state.ticks", 9)
    target.ret("0")
    target.reach("app_step")
    after_zero = _receiver(target)
    target.check("forced zero reached the receiver", after_zero["produced"], 0)
    target.check("receiver counted the second call", after_zero["calls"] > after_value["calls"], True)
