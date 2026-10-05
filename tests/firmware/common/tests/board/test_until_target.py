"""
RU: until(location): цель в текущем кадре достигается, а из вложенной функции кадр завершается раньше.
EN: until(location): a target in the current frame is reached; from a nested function the frame exits first.
"""
from stm32_gdbtest import case

# Lines of the fixture receiver (tests/firmware/src/app_receiver.c).
RECEIVER_COUNT = "app_receiver.c:22"
RECEIVER_PUBLISH = "app_receiver.c:24"


@case("HW_CI_UNTIL_TARGET", timeout_s=60, labels=("api", "showcase", "until"), contracts=("ci_app_api",))
def until_target(target):
    target.reach("app_receiver_step")
    reached = target.until(RECEIVER_COUNT)
    target.check("the line in the current frame was reached", reached["outcome"], "reached")
    target.check("the stop address is a target", reached["stop"]["pc"] in reached["targets"], True)
    target.check("the produced value is stored", target.read("app_received.produced"),
                 target.read("app_state.ticks") + 1)

    # From the producer the target lies in the caller: the producer returns first.
    target.reach("app_step")
    exited = target.until(RECEIVER_PUBLISH)
    target.check("the producer frame exited first", exited["outcome"], "frame_exited")
    target.check("the stop is back in the receiver", target.frames(1)["frames"][0]["name"], "app_receiver_step")
