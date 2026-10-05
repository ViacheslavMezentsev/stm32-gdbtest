"""
RU: Принудительный возврат со значением: перенос значения и отказы до команды.
EN: Forced return with a value: the transfer of the value and refusals before the command.
"""
from stm32_gdbtest import case, ApiError, case


# The receiver publishes the value the producer returned, so app_state proves the transfer.
@case("HW_CI_RET_VALUE", timeout_s=60, labels=("api", "ret", "invoke"), contracts=("ci_app_api",))
def ret_value(target):
    target.write("app_state.ticks", 41)
    target.reach("app_step")

    # A forced value must reach the caller instead of the producer's own result.
    forced = target.ret(42)
    target.check("ret reports the operation", forced["operation"], "ret")
    target.check("ret names the producer", forced["function"], "app_step")
    target.check("ret names the caller", forced["caller"], "app_receiver_step")
    target.check("ret reports the supplied value", forced["supplied"], 42)
    target.check("ret reports the applied value", forced["applied"], 42)
    target.check("ret encodes the declared type", forced["command"], "return (uint32_t)0x2a")
    target.check("ret recorded the mutation", target.report["mutations"][-1]["operation"], "ret")

    # The receiver consumes the forced value in its own body, which publishes it there.
    target.step(4, unit="instruction", mode="into")
    target.check("the receiver copied the forced value",
                 target.read("app_received.produced"), 42)

    # Refusals happen in the function frame and before anything is executed.
    target.reach("app_step")
    mutations = len(target.report["mutations"])
    try:
        target.ret(1 << 40)
    except ApiError as error:
        target.check("out-of-range code", error.details["code"], "out_of_range")
        target.check("out-of-range effect", error.details["effect"], "none")
        target.check("out-of-range reports the width", error.details["width"], 32)
        target.check("out-of-range reports the high bound", error.details["high"], 0xFFFFFFFF)
    else:
        target.check("an out-of-range value must be refused", False, True)
    target.check("a refused value is not recorded", len(target.report["mutations"]), mutations)

    # A bare return completes the frame without a value.
    target.reach("app_step")
    bare = target.ret()
    target.check("bare ret uses the plain command", bare["command"], "return")
    target.check("bare ret applies no value", bare["applied"], None)

    # The 0.2.x alias still accepts a GDB expression.
    target.reach("app_step")
    alias = target.ret("0")
    target.check("the alias returns a result", alias["operation"], "ret")
    target.check("the alias passes the expression through", alias["command"], "return 0")
