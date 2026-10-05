"""
RU: Типизированное чтение объектов приложения и проверяемая запись значения.
EN: Typed reads of application objects and a verified write of one value.
"""
from stm32_gdbtest import case


# Read the application state as a structured object with the keys the firmware declares.
@case("HW_CI_READ_WRITE", labels=("api", "read", "write"), contracts=("ci_app_api",))
def read_write(target):
    target.reach("app_loop")

    # A struct read returns plain Python values keyed by the declared field names.
    state = target.read("app_state")
    target.check("struct read returns a mapping", type(state) is dict, True)
    target.check("struct read keeps the declared fields", sorted(state), ["led", "ticks"])
    target.check("struct fields are plain integers",
                 all(type(value) is int for value in state.values()), True)

    # A single member read and a field set agree with the struct read.
    target.check("member read agrees with the struct", target.read("app_state.ticks"),
                 state["ticks"])
    fields = target.read("app_state", fields={"ticks": None})
    target.check("field set returns the requested member", sorted(fields), ["ticks"])
    target.check("field set agrees with the struct", fields["ticks"], state["ticks"])

    # The counter is a uint32_t object in RAM, so a write must be verified by read-back.
    before = target.read("app_state.ticks")
    result = target.write("app_state.ticks", 41)
    target.check("write reports the previous value", result["before"], before)
    target.check("write reports the written value", result["after"], 41)
    target.check("write is verified", result["verified"], True)
    target.check("the object holds the written value", target.read("app_state.ticks"), 41)

    # The journal kept both the read-back effect and the mutation record.
    target.check("mutation recorded", target.report["mutations"][-1]["expression"],
                 "app_state.ticks")
    target.check("mutation recorded the new value", target.report["mutations"][-1]["after"], 41)

    # The application resumes from the written value on the next iteration.
    target.reach("app_loop")
    target.check("the application used the written value", target.read("app_state.ticks"), 42)
