"""
RU: Профиль прогона: проверка окружения, в котором запущен сценарий.
EN: Run profile: an environment check of the run the scenario executes in.
"""
from stm32_gdbtest import case


def refuses(target, name, mutate):
    try:
        mutate()
    except TypeError:
        target.check(name, True, True)
    else:
        target.check(name, False, True)


@case("HW_CI_PROFILE", timeout_s=45, labels=("api", "profile"), contracts=("ci_app_api",))
def run_profile(target):
    profile = target.profile

    # The chip answers as target.toml describes it: identity register and flash size.
    identity = profile["identity"]
    chip = target.value(f"*(volatile unsigned int *)0x{identity['address']:08X}") & identity["mask"]
    target.check(f"chip identity 0x{chip:03X} matches {profile['mcu']}", chip, identity["value"])
    flash_kb = target.evaluate(f"*(volatile unsigned short *)0x{profile['flash_size_address']:08X}")
    target.check(f"chip flash {flash_kb} KiB covers the profile",
                 flash_kb * 1024 >= profile["flash_size"], True)

    # The flashed image starts with a vector table: the initial stack lies in SRAM, reset in the flash.
    vectors = target.memory(profile["flash_start"], 8)
    stack, reset = int.from_bytes(vectors[:4], "little"), int.from_bytes(vectors[4:], "little")
    target.check_range("initial stack pointer in SRAM", stack, 0x20000000, 0x20100000)
    target.check_range("reset vector in the profile flash", reset & ~1,
                       profile["flash_start"], profile["flash_start"] + profile["flash_size"] - 1)
    target.check("reset vector is Thumb code", reset & 1, 1)

    # The case section is the scenario that is running now.
    target.check("case id", profile.case["id"], "HW_CI_PROFILE")
    target.check("case function", profile.case["function"], "run_profile")
    target.check("case timeout", profile.case["timeout_s"], 45)
    target.check("case contracts", list(profile.case["contracts"]), ["ci_app_api"])

    # The stand section names a supported backend and server placement.
    stand = profile.stand
    target.check(f"stand backend {stand['backend']}", stand["backend"] in ("openocd", "jlink"), True)
    target.check(f"stand server {stand['server']}", stand["server"] in ("local", "remote"), True)
    target.check("stand speed is unset or positive",
                 stand.get("speed_khz") is None or stand["speed_khz"] > 0, True)

    # The captured files carry digests; a target.toml key reports its file as the origin.
    target.check("target.toml digest", len(profile.files["target"]["sha256"]), 64)
    origin = profile.origin("mcu")
    target.check("mcu comes from target.toml", (origin["state"], origin["file"]),
                 ("file", profile.files["target"]["reference"]))
    target.check("effective records limit", profile.get("api.records.max_records", 0) > 0, True)
    target.check("reset command", profile.get("api.reset.command") in ("monitor reset", "monitor reset halt"),
                 True)

    # The GDB section learns at the first stop whether this GDB reports stop details.
    target.check("gdb version known", bool(profile.gdb["version"]), True)
    target.reach("app_loop")
    details = profile.gdb["stop_details"]
    target.check(f"stop details known after a stop ({details})", details in (True, False), True)
    target.record("profile", profile.to_dict())

    # Every section is read-only.
    refuses(target, "profile refuses assignment", lambda: profile.case.__setitem__("id", "X"))
    refuses(target, "nested api refuses assignment",
            lambda: profile.api["records"].__setitem__("max_records", 1))
