"""
RU: Профиль прогона: проверка окружения, в котором запущен сценарий.
EN: Run profile: an environment check of the run the scenario executes in.
"""
from stm32_gdbtest import case, one_of, within


# SRAM window of the STM32 Cortex-M parts used by the CI profiles.
SRAM = within(0x20000000, 0x200FFFFF)


# A read-only section raises TypeError on item assignment.
def refuses(t, name, mapping, key, value):
    try:
        mapping[key] = value
    except TypeError:
        t.check(name, True)
    else:
        t.check(name, False)


# Check the run environment through the profile: chip, image, case, stand, files, data, build and GDB.
@case("HW_CI_PROFILE", timeout_s=45, labels=("api", "profile"), contracts=("ci_app_api",))
def run_profile(t):
    profile = t.profile

    # The chip answers as target.toml describes it: identity register and flash size.
    identity = profile["identity"]
    chip = t.evaluate(f"*(volatile unsigned int *)0x{identity['address']:08X}") & identity["mask"]
    t.check(f"chip identity 0x{chip:03X} matches {profile['mcu']}", chip, identity["value"])
    flash_kb = t.evaluate(f"*(volatile unsigned short *)0x{profile['flash_size_address']:08X}")
    t.check(f"chip flash {flash_kb} KiB covers the profile", flash_kb * 1024 >= profile["flash_size"])

    # The flashed image starts with a vector table: the initial stack lies in SRAM, reset in the flash.
    vectors = t.memory(profile["flash_start"], 8)
    stack, reset = int.from_bytes(vectors[:4], "little"), int.from_bytes(vectors[4:], "little")
    flash = within(profile["flash_start"], profile["flash_start"] + profile["flash_size"] - 1)
    t.check("initial stack pointer in SRAM", stack, SRAM)
    t.check("reset vector in the profile flash", reset & ~1, flash)
    t.check("reset vector is Thumb code", reset & 1)

    # The case section is the scenario that is running now. These are Python values, not GDB
    # expressions, so they are separate checks: a string cell of check(rows) is evaluated by GDB.
    t.check("case id", profile.case["id"], "HW_CI_PROFILE")
    t.check("case function", profile.case["function"], "run_profile")
    t.check("case timeout", profile.case["timeout_s"], 45)
    t.check("case contracts", list(profile.case["contracts"]), ["ci_app_api"])

    # The stand section names a supported backend and server placement. The list follows the backends the
    # module loads: OpenOCD, ST-LINK GDB Server and J-Link.
    stand = profile.stand
    t.check("stand backend", stand["backend"], one_of("openocd", "stlink", "jlink"))
    t.check("stand server", stand["server"], one_of("local", "remote"))
    t.check("stand speed is unset or positive", stand.get("speed_khz") is None or stand["speed_khz"] > 0)

    # The captured files carry digests; a target.toml key reports its file as the origin.
    t.check("target.toml digest", len(profile.files["target"]["sha256"]), 64)
    origin = profile.origin("mcu")
    t.check("mcu comes from target.toml", (origin["state"], origin["file"]),
            ("file", profile.files["target"]["reference"]))
    t.check("effective records limit", profile.get("api.records.max_records", 0), within(1, 1024))

    # The run resolves the reset command from the dialect of the backend and publishes it to the scenario;
    # the scenario does not read `api.toml` for it (ТЗ API 6.6, schema 2 of the target profile).
    t.check("reset command", stand["reset_command"],
            one_of("monitor reset", "monitor reset halt", "monitor reset init"))

    # The project data file board.toml is declared in session.toml [data] and captured with the run.
    board = profile.data["board"]["board"]
    t.check(f"board name {board['name']}", bool(board["name"]))
    t.check(f"board LED {board['led']}", board["led"][:1] == "P" and board["led"][2:].isdigit())
    t.check("board.toml is the origin of the LED", profile.origin("data.board.board.led")["file"], "board.toml")

    # The build section summarizes the build manifest: compiler, Cube package, CMSIS and defines.
    build = profile.build
    t.check("build manifest present", build is not None)
    t.check("GCC compiled the firmware", [item["name"] for item in build["compilers"]], ["arm-none-eabi-gcc"])
    t.check("CMSIS headers are declared", any(name.endswith("CMSIS") for name in build["libraries"]))
    t.check("CMSIS-only firmware: no HAL", "USE_HAL_DRIVER" in build["defines"], False)

    # The GDB section learns at the first stop whether this GDB reports stop details.
    t.check("gdb version known", bool(profile.gdb["version"]))
    t.reach("app_loop")
    t.check("stop details known after a stop", profile.gdb["stop_details"], one_of(True, False))
    t.record("profile", profile)

    # Every section is read-only.
    refuses(t, "profile refuses assignment", profile.case, "id", "X")
    refuses(t, "nested api refuses assignment", profile.api["records"], "max_records", 1)
    refuses(t, "data refuses assignment", board, "led", "PA0")
