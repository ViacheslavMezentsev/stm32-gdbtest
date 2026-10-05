"""
RU: Принудительный возврат со значением: перенос значения и отказы до команды.
EN: Forced return with a value: the transfer of the value and refusals before the command.
"""
from stm32_gdbtest import case, ApiError, case


# The receiver publishes the value the producer returned, so app_state proves the transfer.
@case("HW_CI_RET_VALUE", timeout_s=60, labels=("api", "ret", "invoke"), contracts=("ci_app_api",))
def ret_value(t):
    t.write("app_state.ticks", 41)
    t.reach("app_step")

    # A forced value must reach the caller instead of the producer's own result.
    forced = t.ret(42)
    t.check("ret reports the operation", forced["operation"], "ret")
    t.check("ret names the producer", forced["function"], "app_step")
    t.check("ret names the caller", forced["caller"], "app_receiver_step")
    t.check("ret reports the supplied value", forced["supplied"], 42)
    t.check("ret reports the applied value", forced["applied"], 42)
    t.check("ret encodes the declared type", forced["command"], "return (uint32_t)0x2a")
    t.check("ret recorded the mutation", t.report["mutations"][-1]["operation"], "ret")

    # The receiver consumes the forced value in its own body, which publishes it there.
    t.step(4, unit="instruction", mode="into")
    t.check("the receiver copied the forced value",
                 t.read("app_received.produced"), 42)

    # Refusals happen in the function frame and before anything is executed.
    t.reach("app_step")
    mutations = len(t.report["mutations"])
    try:
        t.ret(1 << 40)
    except ApiError as error:
        t.check("out-of-range code", error.details["code"], "out_of_range")
        t.check("out-of-range effect", error.details["effect"], "none")
        t.check("out-of-range reports the width", error.details["width"], 32)
        t.check("out-of-range reports the high bound", error.details["high"], 0xFFFFFFFF)
    else:
        t.check("an out-of-range value must be refused", False, True)
    t.check("a refused value is not recorded", len(t.report["mutations"]), mutations)

    # A bare return completes the frame without a value.
    t.reach("app_step")
    bare = t.ret()
    t.check("bare ret uses the plain command", bare["command"], "return")
    t.check("bare ret applies no value", bare["applied"], None)

    # The 0.2.x alias still accepts a GDB expression.
    t.reach("app_step")
    alias = t.ret("0")
    t.check("the alias returns a result", alias["operation"], "ret")
    t.check("the alias passes the expression through", alias["command"], "return 0")
