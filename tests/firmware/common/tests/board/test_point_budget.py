"""
RU: Бюджет точек по профилю: отказ сверх лимита, выключенная точка не занимает слот, clear() освобождает все.
EN: The profile point budget: refusal over the limit, a disabled point holds no slot, clear() frees all.
"""
from stm32_gdbtest import ApiError, case

LOCATIONS = ("app_step", "app_receiver_step", "board_led_toggle", "board_adc_sample", "board_delay_ms",
             "app_loop", "main", "board_init")


def refused(target, name, action):
    try:
        action()
    except ApiError as error:
        target.check(name, error.details["code"], "limit_exceeded")
    else:
        target.check(name, "accepted", "limit_exceeded")


@case("HW_CI_POINT_BUDGET", timeout_s=45, labels=("api", "showcase", "breakpoint"), contracts=("ci_app_api",))
def point_budget(target):
    target.reach("app_loop")
    limit = target.profile["breakpoint_limit"]
    guards = target.profile["fault_handlers"]
    # The fault guards set by the agent at boot already hold slots of the same budget.
    busy = sum(point.active for point in target.owned)
    target.check("the fault guards hold their slots", busy, len(guards))
    free = limit - busy
    target.check_range("the free budget fits the locations", free, 1, len(LOCATIONS) - 1)

    points = []
    for location in LOCATIONS[:free]:
        point = target.breakpoint(location)
        symbol = target.symbol(location)
        if symbol["size"]:
            target.check_range(f"{location} point lies in the function", point.addresses[0],
                               symbol["address"], symbol["address"] + symbol["size"] - 1)
        points.append(point)
    spare = LOCATIONS[free]
    refused(target, "one point over the budget is refused", lambda: target.breakpoint(spare))

    # A disabled point frees its slot; enabling it again would exceed the budget.
    points[0].disable()
    extra = target.breakpoint(spare)
    target.check("the freed slot was used", extra.active, True)
    refused(target, "enabling over the budget is refused", points[0].enable)

    target.clear()
    target.check("clear removed every point, guards included",
                 [point.id for point in target.owned if point.active], [])

    # The scenario re-arms the fault guards from the profile; the rest of the budget is free again.
    for name in guards:
        target.breakpoint(name)
    with target.breakpoint("app_step") as again:
        target.check("the budget is free again", again.active, True)
