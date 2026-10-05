"""
RU: Чтение регистров кадра: счётчик команд, указатель стека и регистры общего назначения.
EN: Frame register reads: the program counter, the stack pointer and general-purpose registers.
"""
from stm32_gdbtest import case, within


# SRAM window of the STM32 Cortex-M parts used by the CI profiles.
SRAM = within(0x20000000, 0x200FFFFF)


# Registers are read by name; the program counter prefers the frame accessor.
@case("HW_CI_REGISTERS", timeout_s=45, labels=("api", "registers"), contracts=("ci_app_api",))
def read_registers(t):
    t.reach("app_loop")

    # The program counter comes from the frame and points at a Thumb instruction in Flash.
    flash = within(t.profile["flash_start"], t.profile["flash_start"] + t.profile["flash_size"] - 1)
    core = t.registers("pc", "sp")
    t.check("pc is an integer", type(core["pc"]) is int)
    t.check("pc points into flash", core["pc"], flash)

    # GDB reports an instruction address, so the thumb bit of the raw register is not set.
    t.check("the pc has no thumb bit", core["pc"] % 2, 0)
    t.check("sp is an integer", type(core["sp"]) is int)

    # The stack lives in the cortex-m sram window; its exact size is not part of the profile.
    t.check("sp points into ram", core["sp"], SRAM)
    t.check("sp is doubleword aligned at the call boundary (AAPCS)", core["sp"] % 8, 0)

    # General-purpose registers are read by name as well and stay inside 32 bits.
    general = t.registers("r0", "r1", "r2", "r3")
    t.check("all requested registers are present", sorted(general), ["r0", "r1", "r2", "r3"])
    t.check("register values are integers", all(type(value) is int for value in general.values()))
    t.check("register values stay inside 32 bits", all(0 <= value <= 0xFFFFFFFF for value in general.values()))

    # The frame accessor is the source of the pc, so a second read is stable.
    t.check("the pc read is stable", t.registers("pc")["pc"], core["pc"])

    # Unknown names and empty requests are refused.
    with t.refused("read_failed", name="an unknown register is refused") as failure:
        t.registers("api030_no_such_register")
    t.check("unknown register keeps the cause", failure.error.__cause__ is not None)
    with t.refused("invalid_names", name="an empty request is refused"):
        t.registers()
