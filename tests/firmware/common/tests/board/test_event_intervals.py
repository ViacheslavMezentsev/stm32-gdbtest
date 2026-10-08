"""
RU: Модель событий и интервалов без чтения MCU.
EN: Model events and intervals without reading the MCU.
"""
from fractions import Fraction
from time import monotonic, sleep
from statistics import mean
from stm32_gdbtest import case


# Build a plain record payload from an already sampled up-counter.
def event(counter, *, clock, epoch, modulus, frequency_hz, observation, order):
    # Reject bool and non-integer counter metadata.
    for name, value in (("counter", counter), ("modulus", modulus), ("frequency_hz", frequency_hz), ("order", order)):
        if type(value) is not int:
            raise ValueError(name + " must be an integer")
    if modulus < 2 or not 0 <= counter < modulus or frequency_hz <= 0 or order < 0:
        raise ValueError("invalid counter domain")

    # Clock identity and observation context must be explicit.
    for value in (clock, epoch, observation):
        if type(value) is not str or not value:
            raise ValueError("clock, epoch and observation must be named")
    return dict(counter=counter, clock=clock, epoch=epoch, modulus=modulus,
                frequency_hz=frequency_hz, observation=observation, order=order)


# The bound is an external assumption, not something two counter samples can prove.
def interval(start, end, *, max_ticks):
    start = event(**start)
    end = event(**end)

    # Pair only events from the same clock domain and epoch.
    for key in ("clock", "epoch", "modulus", "frequency_hz", "observation"):
        if start[key] != end[key]:
            raise ValueError("incompatible " + key)
    if end["order"] <= start["order"]:
        raise ValueError("event order must increase")
    if type(max_ticks) is not int or not 0 <= max_ticks < start["modulus"]:
        raise ValueError("independent bound below one period required")

    ticks = (end["counter"] - start["counter"]) % start["modulus"]
    if ticks > max_ticks:
        raise ValueError("interval exceeds bound")
    seconds = Fraction(ticks, start["frequency_hz"])
    return dict(ticks=ticks, seconds_numerator=seconds.numerator, seconds_denominator=seconds.denominator,
                clock=start["clock"], epoch=start["epoch"], observation=start["observation"],
                max_ticks=max_ticks, single_period_assumed=True)


# Observe three real delay calls using the firmware tick and retained runtime records.
@case("HW_CI_EVENT_INTERVALS", timeout_s=60, contracts=("ci_app_api",))
def event_intervals(t):
    t.reach("app_loop")
    core_hz = t.read("SystemCoreClock")
    reload = t.evaluate("*(unsigned int *)0xE000E014")
    t.record("clock.config", {"source": "board_ticks_ms", "core_hz": core_hz, "reload": reload,
                              "frequency_hz": 1000, "calibrated": False})
    t.check("nominal SysTick reload", reload, core_hz // 1000 - 1)
    common = dict(clock="board_ticks_ms", epoch="current-boot", modulus=2**32,
                  frequency_hz=1000, observation="breakpoint-snapshot")

    # Each pair brackets a delay call; host sleep only tests stability during a halt.
    for index in range(3):
        if index:
            t.reach("app_loop")
        t.reach("board_delay_ms")
        requested = t.read("delay_ms")
        t.check("expected loop delay", requested, 500)
        begin = event(t.read("board_ticks_ms"), order=index * 2, **common)
        t.record("event.begin", begin)
        host_start = monotonic()
        sleep(0.15)
        halted_counter = t.read("board_ticks_ms")
        t.record("event.halt", {"before": begin["counter"], "after": halted_counter,
                                "host_seconds": monotonic() - host_start})
        t.check("software tick stable while halted", halted_counter, begin["counter"])
        t.finish()
        t.record("event.end", event(t.read("board_ticks_ms"), order=index * 2 + 1, **common))

    # Calculate from retained snapshots; do not reread the target while reducing data.
    begins = [record["data"] for record in t.records("event.begin")]
    ends = [record["data"] for record in t.records("event.end")]
    t.check("complete endpoint pairs", [len(begins), len(ends)], [3, 3])
    ticks = []

    # Preserve each derived interval before checking its bounds.
    for begin, end in zip(begins, ends):
        measured = interval(begin, end, max_ticks=60000)
        t.record("event.interval", measured)
        t.check("nominal delay ticks", 500 <= measured["ticks"] <= 502)
        ticks.append(measured["ticks"])
    t.record("event.summary", {"count": len(ticks), "mean_ticks": mean(ticks), "nominal_hz": 1000})
