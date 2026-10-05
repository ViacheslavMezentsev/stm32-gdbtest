"""
RU: Вызов функции прошивки на остановленном ядре: аргументы, результат и отказы.
EN: Calling a firmware function on the halted core: arguments, result and refusals.
"""
from stm32_gdbtest import case


# The call runs the real function, so its effect is visible in the application state.
@case("HW_CI_CALL", timeout_s=60, labels=("api", "call", "invoke"), contracts=("ci_app_api",))
def call_function(t):
    t.reach("app_loop")
    before = t.read("app_state.ticks")

    # The producer increments the state it is given and returns the new count.
    result = t.call("app_step", "&app_state", 1)
    t.check("call reports the operation", result["operation"], "call")
    t.check("call reports the function", result["function"], "app_step")
    t.check("call passes the arguments", result["arguments"], ["&app_state", 1])
    t.check("call builds the expression", result["expression"], "app_step(&app_state, 1)")
    t.check("call reports a returned value", result["outcome"], "returned")
    t.check("call reports the value as available", result["return_state"], "available")
    t.check("call returned the incremented count", result["return_value"], before + 1)
    t.check("the function changed the application state",
                 t.read("app_state.ticks"), before + 1)
    t.check("call recorded the mutation", t.report["mutations"][-1]["operation"], "call")

    # A void function runs as well and reports that it has no value.
    void_call = t.call("board_led_toggle")
    t.check("a void call reports no value", void_call["return_state"], "void")
    t.check("a void call passes no arguments", void_call["arguments"], [])

    # Refusals happen before the call and leave no mutation behind.
    mutations = len(t.report["mutations"])
    with t.refused("unsupported_argument", effect="none", name="an unsupported argument is refused"):
        t.call("app_step", object())
    with t.refused("invalid_function", name="an invalid name is refused"):
        t.call("no such function")
    t.check("refusals are not recorded", len(t.report["mutations"]), mutations)
