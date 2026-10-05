"""
RU: Инъекция: продюсер «вернул» 0, и получатель пошёл в ветку нулевого результата.
EN: Injection: the producer "returned" 0 and the receiver took its zero-result branch.
"""
from stm32_gdbtest import case

RECEIVED = {"produced": None, "calls": None, "took_zero_branch": None}


@case("HW_CI_INJECT_ZERO", timeout_s=60, labels=("api", "showcase", "ret"), contracts=("ci_app_api",))
def inject_zero(t):
    t.reach("app_step")
    before = t.read("app_received", fields=RECEIVED)
    ticks = t.read("app_state.ticks")

    # Leave the producer before its body runs: the caller receives 0 and its copy stays untouched.
    t.ret("0")
    # Let the receiver finish: it reacts to the zero and publishes its untouched copy.
    t.check("the receiver returned to the loop", t.finish()["function"], "app_loop")
    after = t.read("app_received", fields=RECEIVED)
    t.check([
        ("receiver stored the injected zero", after["produced"], 0),
        ("receiver took the zero branch", after["took_zero_branch"], 1),
        ("receiver counted the call", after["calls"], before["calls"] + 1),
    ])
    t.check("the published state kept the old count", t.read("app_state.ticks"), ticks)

    # The next call runs normally; at the entry of the one after it the zero branch is clear again.
    t.reach("app_step")
    t.reach("app_step")
    t.check("a normal result clears the zero branch", t.read("app_received.took_zero_branch"), 0)
