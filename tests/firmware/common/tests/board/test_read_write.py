"""
RU: Типизированное чтение объектов приложения и проверяемая запись значения.
EN: Typed reads of application objects and a verified write of one value.
"""
from stm32_gdbtest import case


# Read the application state as a structured object with the keys the firmware declares.
@case("HW_CI_READ_WRITE", labels=("api", "read", "write"), contracts=("ci_app_api",))
def read_write(t):
    t.reach("app_loop")

    # A struct read returns plain Python values keyed by the declared field names.
    state = t.read("app_state")
    t.check("struct read returns a mapping", type(state) is dict)
    t.check("struct read keeps the declared fields", sorted(state), ["led", "ticks"])
    t.check("struct fields are plain integers", all(type(value) is int for value in state.values()))

    # A single member read and a field set agree with the struct read.
    t.check("member read agrees with the struct", t.read("app_state.ticks"), state["ticks"])
    fields = t.read("app_state", fields={"ticks": None})
    t.check("field set returns the requested member", sorted(fields), ["ticks"])
    t.check("field set agrees with the struct", fields["ticks"], state["ticks"])

    # The counter is a uint32_t object in RAM, so a write must be verified by read-back.
    before = t.read("app_state.ticks")
    result = t.write("app_state.ticks", 41)
    t.check("write reports the previous value", result["before"], before)
    t.check("write reports the written value", result["after"], 41)
    t.check("write is verified", result["verified"])
    t.check("the object holds the written value", t.read("app_state.ticks"), 41)

    # The journal kept both the read-back effect and the mutation record.
    t.check("mutation recorded", t.report["mutations"][-1]["expression"], "app_state.ticks")
    t.check("mutation recorded the new value", t.report["mutations"][-1]["after"], 41)

    # The application resumes from the written value on the next iteration.
    t.reach("app_loop")
    t.check("the application used the written value", t.read("app_state.ticks"), 42)
