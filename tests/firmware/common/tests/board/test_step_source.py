"""
RU: Шаги по строкам: заход в вызов продюсера и шаг над ним.
EN: Source-line steps: stepping into the producer call and over it.
"""
from stm32_gdbtest import case


# Upper bound of source steps before the expected line; the loop stops earlier.
MAX_STEPS = 6


# The two innermost frames of the current stop.
def innermost(t):
    return t.frames(2)["frames"]


# Step by source lines into the producer call and over it.
@case("HW_CI_STEP_SOURCE", timeout_s=90, labels=("api", "showcase", "step"), contracts=("ci_app_api",))
def step_source(t):
    # Stepping into: the receiver's call line leads into the producer.
    t.reach("app_receiver_step")

    # A bounded number of steps: the call line is a few lines below the entry.
    for _ in range(MAX_STEPS):
        t.step(1, unit="source", mode="into")
        if innermost(t)[0]["name"] == "app_step":
            break
    chain = innermost(t)
    t.check("stepped into the producer", chain[0]["name"], "app_step")
    t.check("the producer was called by the receiver", chain[1]["name"], "app_receiver_step")
    t.check("the producer sees the blink mode", t.arguments()["values"]["mode"], 1)
    t.finish()

    # Stepping over: every stop stays in the receiver until the call count advances.
    t.reach("app_receiver_step")
    calls = t.read("app_received.calls")
    frames = []

    # Collect the frame of every step until the call count shows that the call line completed.
    for _ in range(MAX_STEPS):
        t.step(1, unit="source", mode="over")
        frames.append(innermost(t)[0]["name"])
        if t.read("app_received.calls") == calls + 1:
            break
    t.check("stepping over stayed in the receiver", set(frames), {"app_receiver_step"})
    t.check("the call line completed", t.read("app_received.calls"), calls + 1)
