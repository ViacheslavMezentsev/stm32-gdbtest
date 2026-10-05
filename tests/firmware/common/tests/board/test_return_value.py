"""
RU: Значение возврата: finish, регистр r0 и значение, опубликованное получателем, совпадают.
EN: Return value: finish, register r0 and the value published by the receiver agree.
"""
from stm32_gdbtest import case

# The receiver stores the produced value on the line before this one.
RECEIVER_COUNT = "app_receiver.c:22"
SRAM = (0x20000000, 0x200FFFFF)


@case("HW_CI_RETURN_VALUE", timeout_s=60, labels=("api", "showcase", "finish"), contracts=("ci_app_api",))
def return_value(target):
    target.reach("app_step")
    arguments = target.arguments()
    target.check("the frame is the producer", arguments["function"], "app_step")
    target.check("the receiver asks for blinking", arguments["values"]["mode"], target.evaluate("APP_MODE_BLINK"))
    target.check_range("the state copy lives on the stack", arguments["values"]["state"], *SRAM)
    ticks = target.read("state->ticks")

    finished = target.finish()
    target.check("finish returned into the receiver", finished["function"], "app_receiver_step")
    target.check("the value is available", finished["return_state"], "available")
    target.check("the producer returned the incremented count", finished["return_value"], ticks + 1)
    target.check("r0 holds the same value", target.registers("r0")["r0"], finished["return_value"])

    target.until(RECEIVER_COUNT)
    target.check("the receiver published the value", target.read("app_received.produced"),
                 finished["return_value"])
    local = target.locals()
    if "produced" in local["values"]:
        target.check("the receiver's local holds the value", local["values"]["produced"], finished["return_value"])
    else:
        target.record("produced_unavailable", local["unavailable"])
