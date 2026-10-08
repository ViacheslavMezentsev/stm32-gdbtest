"""
RU: Инъекция входа и результата функции с проверкой побочных эффектов и восстановления.
EN: Inject input and return values, checking side effects and restoration.
"""
from contextlib import contextmanager
from stm32_gdbtest import case


# Capture plain values at a stop; records must not retain live GDB objects.
def snapshot(t):
    paths = ("app_state.ticks", "app_state.led", "app_received.produced", "app_received.calls",
             "app_received.took_zero_branch", "app_received.publications")
    return dict(zip(paths, map(t.read, paths)))


# Restore declared RAM inputs only, not time or all effects of resumed execution.
@contextmanager
def inject_inputs(t):
    saved = {path: t.read(path) for path in ("app_state.ticks", "app_state.led")}
    try:
        t.write("app_state.ticks", 0xffffffff)
        yield saved
    finally:
        t.write(list(saved.items()))
        actual = {path: t.read(path) for path in saved}
        t.record("injection.restored", {"expected": saved, "actual": actual})
        t.check("declared inputs restored", actual, saved)


# Confirm the receiver consumed exactly one producer result.
def check_receiver(t, before, after, ticks, led, zero):
    # Check publication and call accounting together.
    t.check([
        ("published ticks", after["app_state.ticks"], ticks),
        ("published led", after["app_state.led"], led),
        ("received result", after["app_received.produced"], ticks),
        ("receiver branch", after["app_received.took_zero_branch"], zero),
        ("one call", (after["app_received.calls"] - before["app_received.calls"]) & 0xffffffff, 1),
        ("one publication", (after["app_received.publications"] - before["app_received.publications"]) & 0xffffffff, 1)
    ])


# Compare natural wraparound with an early return: same branch, different side effects.
@case("HW_CI_EVENT_INJECTION", timeout_s=60, contracts=("ci_app_api",))
def event_injection(t):
    t.reach("app_loop")
    before = snapshot(t)
    t.reach("app_receiver_step")
    t.finish()
    after = snapshot(t)
    t.record("injection.baseline", {"before": before, "after": after})
    check_receiver(t, before, after, (before["app_state.ticks"] + 1) & 0xffffffff, before["app_state.led"] ^ 1, 0)

    # Change the input before the receiver makes its local copy.
    t.reach("app_loop")
    before = snapshot(t)
    with inject_inputs(t):
        t.reach("app_receiver_step")
        t.finish()
        after = snapshot(t)
        t.record("injection.input", {"before": before, "injected_ticks": 0xffffffff, "after": after})
        check_receiver(t, before, after, 0, before["app_state.led"] ^ 1, 1)

    # The early return bypasses the producer's increments and LED toggle.
    t.reach("app_loop")
    before = snapshot(t)
    t.reach("app_step")
    returned = t.ret("0")
    t.finish()
    after = snapshot(t)
    t.record("injection.return", {"before": before, "after": after, "operation": returned})
    t.check("return path received zero", after["app_received.produced"], 0)
    t.check("return path took zero branch", after["app_received.took_zero_branch"], 1)

    # A skipped producer must leave both state fields unchanged.
    for path in ("app_state.ticks", "app_state.led"):
        t.check("skipped producer preserves " + path, after[path], before[path])

    # The caller still consumes and publishes one result.
    for path in ("app_received.calls", "app_received.publications"):
        t.check("return receiver advances " + path, (after[path] - before[path]) & 0xffffffff, 1)

    # Resume normal behavior and prove the injected branch is not persistent.
    t.reach("app_loop")
    before = snapshot(t)
    t.reach("app_receiver_step")
    t.finish()
    after = snapshot(t)
    t.record("injection.normal_again", {"before": before, "after": after})
    check_receiver(t, before, after, (before["app_state.ticks"] + 1) & 0xffffffff, before["app_state.led"] ^ 1, 0)

    # Fail before resuming and check restoration on the exception path.
    t.reach("app_loop")
    before = snapshot(t)
    caught = False
    try:
        with inject_inputs(t):
            t.check("input applied before exception", t.read("app_state.ticks"), 0xffffffff)
            raise RuntimeError("deliberate scenario exception")
    except RuntimeError as error:
        caught = str(error) == "deliberate scenario exception"
    after = snapshot(t)
    t.record("injection.exception", {"caught": caught, "before": before, "after": after})
    t.check("deliberate exception propagated", caught)
    t.check("no execution during exception experiment", after, before)
