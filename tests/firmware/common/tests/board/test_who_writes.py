"""
RU: Кто пишет app_state.ticks: точка наблюдения и цепочка кадров писателя.
EN: Who writes app_state.ticks: a watch point and the writer's frame chain.
"""
from stm32_gdbtest import case, within


@case("HW_CI_WHO_WRITES", timeout_s=60, labels=("api", "showcase", "watch"), contracts=("ci_app_api",))
def who_writes(t):
    t.reach("app_loop")
    state = t.symbol("app_state")
    t.check("app_state is zero-initialized data", state["section"], ".bss")
    before = t.read("app_state.ticks")

    with t.watch("app_state.ticks"):
        stop = t.resume()["stop"]
        t.check("the stop is the watch point", stop["kind"], "watchpoint")
        chain = t.frames(4)["frames"]
        names = [frame["name"] for frame in chain]
        t.record("writer", dict(frames=chain, value=t.read("app_state.ticks")))
        t.check("the writer is the receiver", names[0], "app_receiver_step")
        t.check("the receiver runs from the loop", names[1], "app_loop")
        writer = t.symbol("app_receiver_step")
        if writer["size"]:
            t.check("the stop lies inside the writer", chain[0]["pc"],
                    within(writer["address"], writer["address"] + writer["size"] - 1))
        t.check("the published count advanced by one", t.read("app_state.ticks"), before + 1)
