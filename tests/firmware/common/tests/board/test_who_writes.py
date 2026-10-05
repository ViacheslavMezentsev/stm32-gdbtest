"""
RU: Кто пишет app_state.ticks: точка наблюдения и цепочка кадров писателя.
EN: Who writes app_state.ticks: a watch point and the writer's frame chain.
"""
from stm32_gdbtest import case


@case("HW_CI_WHO_WRITES", timeout_s=60, labels=("api", "showcase", "watch"), contracts=("ci_app_api",))
def who_writes(target):
    target.reach("app_loop")
    state = target.symbol("app_state")
    target.check("app_state is zero-initialized data", state["section"], ".bss")
    before = target.read("app_state.ticks")

    with target.watch("app_state.ticks"):
        stop = target.resume()["stop"]
        target.check("the stop is the watch point", stop["kind"], "watchpoint")
        chain = target.frames(4)["frames"]
        names = [frame["name"] for frame in chain]
        target.record("writer", dict(frames=chain, value=target.read("app_state.ticks")))
        target.check("the writer is the receiver", names[0], "app_receiver_step")
        target.check("the receiver runs from the loop", names[1], "app_loop")
        writer = target.symbol("app_receiver_step")
        if writer["size"]:
            target.check_range("the stop lies inside the writer", chain[0]["pc"],
                               writer["address"], writer["address"] + writer["size"] - 1)
        target.check("the published count advanced by one", target.read("app_state.ticks"), before + 1)
