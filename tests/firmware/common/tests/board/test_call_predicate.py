"""
RU: Вызов функции прошивки как проверки: состояние снимается до вызова и восстанавливается после.
EN: Calling a firmware function as a check: the state is saved before the call and restored after it.
"""
from stm32_gdbtest import case


@case("HW_CI_CALL_PREDICATE", timeout_s=60, labels=("api", "showcase", "call"), contracts=("ci_app_api",))
def call_predicate(target):
    target.reach("app_loop")
    state = target.symbol("app_state")
    snapshot = target.memory(state["address"], state["size"])
    before = target.read("app_state", fields={"ticks": None, "led": None})

    for mode, toggles in (("APP_MODE_IDLE", False), ("APP_MODE_BLINK", True)):
        result = target.call("app_step", "&app_state", mode)
        target.check(f"{mode}: the producer counts", result["return_value"], before["ticks"] + 1)
        target.check(f"{mode}: the LED flag", target.read("app_state.led"), before["led"] ^ int(toggles))

        # Restoring the bytes makes the call a side-effect-free predicate.
        target.write_memory(state["address"], snapshot)
        target.check(f"{mode}: the state bytes are restored",
                     target.memory(state["address"], state["size"]).hex(), snapshot.hex())
    target.check("the application continues from the saved count", target.read("app_state.ticks"), before["ticks"])
