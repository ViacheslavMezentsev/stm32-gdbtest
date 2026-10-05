"""
RU: Точка наблюдения: адресуемый объект, остановка на записи и отказы.
EN: A watch point: an addressable object, the write stop and refusals.
"""
from stm32_gdbtest import case, ApiError, case


# A watch point stops the core when the firmware writes the watched object.
@case("HW_CI_WATCH", timeout_s=60, labels=("api", "watch"), contracts=("ci_app_api",))
def watch_object(target):
    target.reach("app_loop")

    # The firmware is still running here, so a watch point on its state must fire on the next write.
    with target.watch("app_state.ticks") as point:
        before = target.read("app_state.ticks")
        result = target.resume()
        stop = result["stop"]
        target.check("the stop is a watch point", stop["kind"], "watchpoint")
        # The native reason is a hint: OpenOCD names the trigger, J-Link reports none at all.
        target.check("the stop names the watch point",
                     stop["native_reason"] in (None, "", "watchpoint-trigger"), True)
        target.check("the watched object changed", target.read("app_state.ticks") > before, True)

    # The point is gone after the context manager; the stand keeps its own fault guard.
    target.check("no watch point stays active",
                 [item.id for item in target.owned if item.watch and item.active], [])
    target.check("the watch point became inactive", point.active, False)

    # A whole structure of eight bytes is a valid watch target, exactly like its field.
    with target.watch("app_state") as whole:
        target.check("a whole structure can be watched", whole.watch, True)
        target.check("the structure point is active", whole.active, True)

    # An unknown object and a non-object expression are refused before the debugger is touched.
    for path, code in (("api030_no_such_object", "invalid_path"),
                       ("app_state.ticks + 1", "not_addressable")):
        try:
            target.watch(path)
        except ApiError as error:
            target.check("refused watch code", error.details["code"], code)
            target.check("refused watch stage", error.details["stage"], "validation")
        else:
            target.check("an unwatchable object must be refused", False, True)
    target.check("refusals leave no watch point behind",
                 [item.id for item in target.owned if item.watch], [])
