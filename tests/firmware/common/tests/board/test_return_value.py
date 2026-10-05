"""
RU: Значение возврата: finish, регистр r0 и значение, опубликованное получателем, совпадают.
EN: Return value: finish, register r0 and the value published by the receiver agree.
"""
from stm32_gdbtest import case, within


# SRAM window of the STM32 Cortex-M parts used by the CI profiles.
SRAM = within(0x20000000, 0x200FFFFF)


# Compare three views of one return value: finish, register r0 and what the receiver published.
@case("HW_CI_RETURN_VALUE", timeout_s=60, labels=("api", "showcase", "finish"), contracts=("ci_app_api",))
def return_value(t):
    t.reach("app_step")
    arguments = t.arguments()
    t.check("the frame is the producer", arguments["function"], "app_step")
    t.check("the receiver asks for blinking", arguments["values"]["mode"], t.evaluate("APP_MODE_BLINK"))
    t.check("the state copy lives on the stack", arguments["values"]["state"], SRAM)
    ticks = t.read("state->ticks")

    finished = t.finish()
    t.check("finish returned into the receiver", finished["function"], "app_receiver_step")
    t.check("the value is available", finished["return_state"], "available")
    t.check("the producer returned the incremented count", finished["return_value"], ticks + 1)
    t.check("r0 holds the same value", t.registers("r0")["r0"], finished["return_value"])

    # Let the receiver finish: it stores the value and publishes the incremented count.
    t.check("the receiver returned to the loop", t.finish()["function"], "app_loop")
    t.check("the receiver stored the value", t.read("app_received.produced"), finished["return_value"])
    t.check("the receiver published the count", t.read("app_state.ticks"), finished["return_value"])
