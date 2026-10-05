"""
RU: Вызов функции прошивки как проверки: состояние снимается до вызова и восстанавливается после.
EN: Calling a firmware function as a check: the state is saved before the call and restored after it.
"""
from stm32_gdbtest import case


# Call the producer as a predicate and restore the state bytes it changed after every call.
@case("HW_CI_CALL_PREDICATE", timeout_s=60, labels=("api", "showcase", "call"), contracts=("ci_app_api",))
def call_predicate(t):
    t.reach("app_loop")
    state = t.symbol("app_state")
    snapshot = t.memory(state["address"], state["size"])
    before = t.read("app_state", fields={"ticks": None, "led": None})

    # Both modes count; only the blink mode toggles the LED flag.
    for mode, toggles in (("APP_MODE_IDLE", False), ("APP_MODE_BLINK", True)):
        result = t.call("app_step", "&app_state", mode)
        t.check(f"{mode}: the producer counts", result["return_value"], before["ticks"] + 1)
        t.check(f"{mode}: the LED flag", t.read("app_state.led"), before["led"] ^ int(toggles))

        # Restoring the bytes makes the call a side-effect-free predicate.
        t.memory(state["address"], snapshot)
        t.check(f"{mode}: the state bytes are restored",
                t.memory(state["address"], state["size"]).hex(), snapshot.hex())
    t.check("the application continues from the saved count", t.read("app_state.ticks"), before["ticks"])
