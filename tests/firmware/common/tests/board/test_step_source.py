"""
RU: Шаги по строкам: заход в вызов продюсера и шаг над ним.
EN: Source-line steps: stepping into the producer call and over it.
"""
from stm32_gdbtest import case

MAX_STEPS = 6


def innermost(target):
    return target.frames(2)["frames"]


@case("HW_CI_STEP_SOURCE", timeout_s=90, labels=("api", "showcase", "step"), contracts=("ci_app_api",))
def step_source(target):
    # Stepping into: the receiver's call line leads into the producer.
    target.reach("app_receiver_step")
    for _ in range(MAX_STEPS):
        target.step(1, unit="source", mode="into")
        if innermost(target)[0]["name"] == "app_step":
            break
    chain = innermost(target)
    target.check("stepped into the producer", chain[0]["name"], "app_step")
    target.check("the producer was called by the receiver", chain[1]["name"], "app_receiver_step")
    target.check("the producer sees the blink mode", target.arguments()["values"]["mode"], 1)
    target.finish()

    # Stepping over: every stop stays in the receiver until the call count advances.
    target.reach("app_receiver_step")
    calls = target.read("app_received.calls")
    frames = []
    for _ in range(MAX_STEPS):
        target.step(1, unit="source", mode="over")
        frames.append(innermost(target)[0]["name"])
        if target.read("app_received.calls") == calls + 1:
            break
    target.check("stepping over stayed in the receiver", set(frames), {"app_receiver_step"})
    target.check("the call line completed", target.read("app_received.calls"), calls + 1)
