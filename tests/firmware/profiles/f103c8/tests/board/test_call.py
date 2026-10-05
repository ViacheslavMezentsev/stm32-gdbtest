"""
RU: Вызов функции прошивки на остановленном ядре: аргументы, результат и отказы.
EN: Calling a firmware function on the halted core: arguments, result and refusals.
"""
from stm32_gdbtest import case, ApiError, case


# The call runs the real function, so its effect is visible in the application state.
@case("HW_CI_CALL", timeout_s=60, labels=("api", "call", "invoke"), contracts=("ci_app_api",))
def call_function(target):
    target.reach("app_loop")
    before = target.read("app_state.ticks")

    # The producer increments the state it is given and returns the new count.
    result = target.call("app_step", "&app_state", 1)
    target.check("call reports the operation", result["operation"], "call")
    target.check("call reports the function", result["function"], "app_step")
    target.check("call passes the arguments", result["arguments"], ["&app_state", 1])
    target.check("call builds the expression", result["expression"], "app_step(&app_state, 1)")
    target.check("call reports a returned value", result["outcome"], "returned")
    target.check("call reports the value as available", result["return_state"], "available")
    target.check("call returned the incremented count", result["return_value"], before + 1)
    target.check("the function changed the application state",
                 target.read("app_state.ticks"), before + 1)
    target.check("call recorded the mutation", target.report["mutations"][-1]["operation"], "call")

    # A void function runs as well and reports that it has no value.
    void_call = target.call("board_led_toggle")
    target.check("a void call reports no value", void_call["return_state"], "void")
    target.check("a void call passes no arguments", void_call["arguments"], [])

    # Refusals happen before the call and leave no mutation behind.
    mutations = len(target.report["mutations"])
    try:
        target.call("app_step", object())
    except ApiError as error:
        target.check("unsupported argument code", error.details["code"], "unsupported_argument")
        target.check("unsupported argument effect", error.details["effect"], "none")
    else:
        target.check("an unsupported argument must be refused", False, True)
    try:
        target.call("no such function")
    except ApiError as error:
        target.check("invalid name code", error.details["code"], "invalid_function")
    else:
        target.check("an invalid name must be refused", False, True)
    target.check("refusals are not recorded", len(target.report["mutations"]), mutations)
