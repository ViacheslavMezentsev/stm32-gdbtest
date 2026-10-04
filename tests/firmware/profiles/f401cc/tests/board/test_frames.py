"""
RU: Цепочка кадров: глубины, имена, счётчики команд и предел обхода.
EN: Frame chain: depths, names, program counters and the walk limit.
"""
from stm32_gdbtest import ApiError, case


# The chain starts at the innermost frame and stops at the limit.
@case("HW_CI_FRAMES", timeout_s=45, labels=("api", "frames"), contracts=("ci_app_api",))
def walk_frames(target):
    target.reach("app_loop")

    # The innermost frame is the function the core stopped in.
    chain = target.frames()
    target.check("frames reports the operation", chain["operation"], "frames")
    target.check("the innermost frame is the stopped function", chain["frames"][0]["name"],
                 "app_loop")
    target.check("the innermost frame has depth zero", chain["frames"][0]["depth"], 0)
    target.check("the innermost frame is a normal frame", chain["frames"][0]["method"], "normal")
    target.check("the innermost frame has a pc", type(chain["frames"][0]["pc"]) is int, True)

    # The caller of the application loop is on the chain, and depths grow outwards.
    names = [entry["name"] for entry in chain["frames"]]
    target.check("the caller is on the chain", "main" in names, True)
    target.check("depths grow outwards",
                 [entry["depth"] for entry in chain["frames"]], list(range(chain["count"])))
    target.check("the count matches the chain", chain["count"], len(chain["frames"]))

    # A limit bounds the walk and reports that it did not complete.
    limited = target.frames(limit=1)
    target.check("the limit is respected", len(limited["frames"]), 1)
    target.check("a bounded walk is incomplete", limited["complete"], False)
    target.check("a bounded walk keeps the innermost frame",
                 limited["frames"][0]["name"], "app_loop")
    full = target.frames(limit=64)
    target.check("a wide walk completes", full["complete"], True)
    target.check("the wide walk keeps the chain", full["count"] >= chain["count"], True)

    # An unusable limit is refused before the chain is walked.
    for limit in (0, -1, "16"):
        try:
            target.frames(limit=limit)
        except ApiError as error:
            target.check("refused limit code", error.details["code"], "invalid_limit")
            target.check("refused limit stage", error.details["stage"], "validation")
        else:
            target.check("an invalid limit must be refused", False, True)
