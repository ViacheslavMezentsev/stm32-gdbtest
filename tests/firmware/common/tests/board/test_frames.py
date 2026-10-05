"""
RU: Цепочка кадров: глубины, имена, счётчики команд и предел обхода.
EN: Frame chain: depths, names, program counters and the walk limit.
"""
from stm32_gdbtest import case


# The chain starts at the innermost frame and stops at the limit.
@case("HW_CI_FRAMES", timeout_s=45, labels=("api", "frames"), contracts=("ci_app_api",))
def walk_frames(t):
    t.reach("app_loop")

    # The innermost frame is the function the core stopped in.
    chain = t.frames()
    t.check("frames reports the operation", chain["operation"], "frames")
    t.check("the innermost frame is the stopped function", chain["frames"][0]["name"], "app_loop")
    t.check("the innermost frame has depth zero", chain["frames"][0]["depth"], 0)
    t.check("the innermost frame is a normal frame", chain["frames"][0]["method"], "normal")
    t.check("the innermost frame has a pc", type(chain["frames"][0]["pc"]) is int)

    # The caller of the application loop is on the chain, and depths grow outwards.
    names = [entry["name"] for entry in chain["frames"]]
    t.check("the caller is on the chain", "main" in names)
    t.check("depths grow outwards", [entry["depth"] for entry in chain["frames"]], list(range(chain["count"])))
    t.check("the count matches the chain", chain["count"], len(chain["frames"]))

    # A limit bounds the walk and reports that it did not complete.
    limited = t.frames(limit=1)
    t.check("the limit is respected", len(limited["frames"]), 1)
    t.check("a bounded walk is incomplete", limited["complete"], False)
    t.check("a bounded walk keeps the innermost frame", limited["frames"][0]["name"], "app_loop")
    full = t.frames(limit=64)
    t.check("a wide walk completes", full["complete"], True)
    t.check("the wide walk keeps the chain", full["count"] >= chain["count"])

    # An unusable limit is refused before the chain is walked.
    for limit in (0, -1, "16"):
        with t.refused("invalid_limit", stage="validation", name=f"invalid limit {limit!r} is refused"):
            t.frames(limit=limit)
