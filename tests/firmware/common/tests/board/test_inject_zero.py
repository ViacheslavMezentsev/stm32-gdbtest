"""
RU: Инъекция: продюсер «вернул» 0, и получатель пошёл в ветку нулевого результата.
EN: Injection: the producer "returned" 0 and the receiver took its zero-result branch.
"""
from stm32_gdbtest import case

# The receiver publishes app_state on this line, after it has stored the produced value and branch.
RECEIVER_PUBLISH = "app_receiver.c:24"
RECEIVED = {"produced": None, "calls": None, "took_zero_branch": None}


@case("HW_CI_INJECT_ZERO", timeout_s=60, labels=("api", "showcase", "ret"), contracts=("ci_app_api",))
def inject_zero(target):
    target.reach("app_step")
    before = target.read("app_received", fields=RECEIVED)
    ticks = target.read("app_state.ticks")

    # Leave the producer before its body runs: the caller receives 0 and its copy stays untouched.
    target.ret("0")
    target.until(RECEIVER_PUBLISH)
    after = target.read("app_received", fields=RECEIVED)
    target.check_table([
        ("receiver stored the injected zero", after["produced"], 0),
        ("receiver took the zero branch", after["took_zero_branch"], 1),
        ("receiver counted the call", after["calls"], before["calls"] + 1),
    ])
    copy = target.locals()["values"]["next"]
    target.check("the skipped producer left the copy unchanged", copy["ticks"], ticks)

    # The next normal call leaves the zero branch again.
    target.reach("app_step")
    target.check("the published state kept the old count", target.read("app_state.ticks"), ticks)
    target.reach("app_step")
    target.check("a normal result clears the zero branch", target.read("app_received.took_zero_branch"), 0)
