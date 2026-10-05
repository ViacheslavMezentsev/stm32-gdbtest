"""
RU: until(location): цель в текущем кадре достигается, а из вложенной функции кадр завершается раньше.
EN: until(location): a target in the current frame is reached; from a nested function the frame exits first.
"""
from stm32_gdbtest import case

# Source lines of the fixture receiver (tests/firmware/src/app_receiver.c). A file:line location breaks
# with any edit of the source; it is used here only because until(file:line) is what this scenario checks.
# Other scenarios name functions and use finish() instead. A host check guards the two lines.
RECEIVER_COUNT = "app_receiver.c:22"
RECEIVER_PUBLISH = "app_receiver.c:24"


@case("HW_CI_UNTIL_TARGET", timeout_s=60, labels=("api", "showcase", "until"), contracts=("ci_app_api",))
def until_target(t):
    t.reach("app_receiver_step")
    reached = t.until(RECEIVER_COUNT)
    t.check("the line in the current frame was reached", reached["outcome"], "reached")
    t.check("the stop address is a target", reached["stop"]["pc"] in reached["targets"])
    t.check("the produced value is stored", t.read("app_received.produced"),
                 t.read("app_state.ticks") + 1)

    # From the producer the target lies in the caller: the producer returns first.
    t.reach("app_step")
    exited = t.until(RECEIVER_PUBLISH)
    t.check("the producer frame exited first", exited["outcome"], "frame_exited")
    t.check("the stop is back in the receiver", t.frames(1)["frames"][0]["name"], "app_receiver_step")
