"""
RU: Значение возврата: finish, регистр r0 и значение, опубликованное получателем, совпадают.
EN: Return value: finish, register r0 and the value published by the receiver agree.
"""
from stm32_gdbtest import case, within

# The receiver stores the produced value on the line before this one.
RECEIVER_COUNT = "app_receiver.c:22"
SRAM = (0x20000000, 0x200FFFFF)


@case("HW_CI_RETURN_VALUE", timeout_s=60, labels=("api", "showcase", "finish"), contracts=("ci_app_api",))
def return_value(t):
    t.reach("app_step")
    arguments = t.arguments()
    t.check("the frame is the producer", arguments["function"], "app_step")
    t.check("the receiver asks for blinking", arguments["values"]["mode"], t.evaluate("APP_MODE_BLINK"))
    t.check("the state copy lives on the stack", arguments["values"]["state"], within(*SRAM))
    ticks = t.read("state->ticks")

    finished = t.finish()
    t.check("finish returned into the receiver", finished["function"], "app_receiver_step")
    t.check("the value is available", finished["return_state"], "available")
    t.check("the producer returned the incremented count", finished["return_value"], ticks + 1)
    t.check("r0 holds the same value", t.registers("r0")["r0"], finished["return_value"])

    t.until(RECEIVER_COUNT)
    t.check("the receiver published the value", t.read("app_received.produced"),
                 finished["return_value"])
    local = t.locals()
    if "produced" in local["values"]:
        t.check("the receiver's local holds the value", local["values"]["produced"], finished["return_value"])
    else:
        t.record("produced_unavailable", local["unavailable"])
