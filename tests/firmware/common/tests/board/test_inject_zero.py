"""
RU: Инъекция: продюсер «вернул» 0, и получатель пошёл в ветку нулевого результата.
EN: Injection: the producer "returned" 0 and the receiver took its zero-result branch.
"""
from stm32_gdbtest import case

# The receiver publishes app_state on this line, after it has stored the produced value and branch.
RECEIVER_PUBLISH = "app_receiver.c:24"
RECEIVED = {"produced": None, "calls": None, "took_zero_branch": None}


@case("HW_CI_INJECT_ZERO", timeout_s=60, labels=("api", "showcase", "ret"), contracts=("ci_app_api",))
def inject_zero(t):
    t.reach("app_step")
    before = t.read("app_received", fields=RECEIVED)
    ticks = t.read("app_state.ticks")

    # Leave the producer before its body runs: the caller receives 0 and its copy stays untouched.
    t.ret("0")
    t.until(RECEIVER_PUBLISH)
    after = t.read("app_received", fields=RECEIVED)
    t.check([
        ("receiver stored the injected zero", after["produced"], 0),
        ("receiver took the zero branch", after["took_zero_branch"], 1),
        ("receiver counted the call", after["calls"], before["calls"] + 1),
    ])
    copy = t.locals()["values"]["next"]
    t.check("the skipped producer left the copy unchanged", copy["ticks"], ticks)

    # The next normal call leaves the zero branch again.
    t.reach("app_step")
    t.check("the published state kept the old count", t.read("app_state.ticks"), ticks)
    t.reach("app_step")
    t.check("a normal result clears the zero branch", t.read("app_received.took_zero_branch"), 0)
