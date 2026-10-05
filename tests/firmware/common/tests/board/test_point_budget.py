"""
RU: Бюджет точек по профилю: отказ сверх лимита, выключенная точка не занимает слот, clear() освобождает все.
EN: The profile point budget: refusal over the limit, a disabled point holds no slot, clear() frees all.
"""
from stm32_gdbtest import case, within

LOCATIONS = ("app_step", "app_receiver_step", "board_led_toggle", "board_adc_sample", "board_delay_ms",
             "app_loop", "main", "board_init")


@case("HW_CI_POINT_BUDGET", timeout_s=45, labels=("api", "showcase", "breakpoint"), contracts=("ci_app_api",))
def point_budget(t):
    t.reach("app_loop")
    limit = t.profile["breakpoint_limit"]
    guards = t.profile["fault_handlers"]
    # The fault guards set by the agent at boot already hold slots of the same budget.
    busy = sum(point.active for point in t.owned)
    t.check("the fault guards hold their slots", busy, len(guards))
    free = limit - busy
    t.check("the free budget fits the locations", free, within(1, len(LOCATIONS) - 1))

    points = []
    for location in LOCATIONS[:free]:
        point = t.breakpoint(location)
        symbol = t.symbol(location)
        if symbol["size"]:
            t.check(f"{location} point lies in the function", point.addresses[0],
                    within(symbol["address"], symbol["address"] + symbol["size"] - 1))
        points.append(point)
    spare = LOCATIONS[free]
    with t.refused("limit_exceeded", name="one point over the budget is refused"):
        t.breakpoint(spare)

    # A disabled point frees its slot; enabling it again would exceed the budget.
    points[0].disable()
    extra = t.breakpoint(spare)
    t.check("the freed slot was used", extra.active, True)
    with t.refused("limit_exceeded", name="enabling over the budget is refused"):
        points[0].enable()

    t.clear()
    t.check("clear removed every point, guards included",
                 [point.id for point in t.owned if point.active], [])

    # The scenario re-arms the fault guards from the profile; the rest of the budget is free again.
    for name in guards:
        t.breakpoint(name)
    with t.breakpoint("app_step") as again:
        t.check("the budget is free again", again.active)
