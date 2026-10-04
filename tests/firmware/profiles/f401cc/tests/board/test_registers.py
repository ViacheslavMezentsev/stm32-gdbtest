"""
RU: Чтение регистров кадра: счётчик команд, указатель стека и регистры общего назначения.
EN: Frame register reads: the program counter, the stack pointer and general-purpose registers.
"""
from stm32_gdbtest import ApiError, case


# Registers are read by name; the program counter prefers the frame accessor.
@case("HW_CI_REGISTERS", timeout_s=45, labels=("api", "registers"), contracts=("ci_app_api",))
def read_registers(target):
    target.reach("app_loop")

    # The program counter comes from the frame and points at a Thumb instruction in Flash.
    flash_start = target.profile["flash_start"]
    flash_end = flash_start + target.profile["flash_size"]
    core = target.registers("pc", "sp")
    target.check("pc is an integer", type(core["pc"]) is int, True)
    target.check("pc points into flash", flash_start <= core["pc"] < flash_end, True)
    # GDB reports an instruction address, so the thumb bit of the raw register is not set.
    target.check("the pc has no thumb bit", core["pc"] % 2, 0)
    target.check("sp is an integer", type(core["sp"]) is int, True)
    # The stack lives in the cortex-m sram window; its exact size is not part of the profile.
    target.check("sp points into ram", 0x20000000 <= core["sp"] < 0x20100000, True)
    target.check("sp is word aligned", core["sp"] % 8, 0)

    # General-purpose registers are read by name as well and stay inside 32 bits.
    general = target.registers("r0", "r1", "r2", "r3")
    target.check("all requested registers are present", sorted(general), ["r0", "r1", "r2", "r3"])
    target.check("register values are integers",
                 all(type(value) is int for value in general.values()), True)
    target.check("register values stay inside 32 bits",
                 all(0 <= value <= 0xFFFFFFFF for value in general.values()), True)

    # The frame accessor is the source of the pc, so a second read is stable.
    target.check("the pc read is stable", target.registers("pc")["pc"], core["pc"])

    # Unknown names and empty requests are refused.
    try:
        target.registers("api030_no_such_register")
    except ApiError as error:
        target.check("unknown register code", error.details["code"], "read_failed")
        target.check("unknown register keeps the cause", error.__cause__ is not None, True)
    else:
        target.check("an unknown register must be refused", False, True)
    try:
        target.registers()
    except ApiError as error:
        target.check("empty request code", error.details["code"], "invalid_names")
    else:
        target.check("an empty request must be refused", False, True)
