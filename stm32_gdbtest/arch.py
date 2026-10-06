"""Architecture adapters: which functions guard against faults and which registers describe a failure.

Portability P1-7. The adapter is chosen by the machine of the firmware ELF (`objdump -h` file format); only
Cortex-M exists, and it reproduces the profile-driven behaviour of schema 1: breakpoints on `fault_handlers`,
diagnostics from `core_registers` (by name) and `diagnostic_registers` (memory words).
"""


class CortexM:
    """ARMv6-M/ARMv7-M: dedicated fault handlers, so a breakpoint on each one is a fault guard."""
    name = "cortex-m"

    def fault_guards(self, profile):
        return list(profile["fault_handlers"])

    def diagnostic_registers(self, profile):
        return list(profile["core_registers"])

    def diagnostic_memory(self, profile):
        return dict(profile["diagnostic_registers"])


ADAPTERS = {"arm": CortexM()}
DEFAULT_MACHINE = "arm"


def adapter(machine):
    """Adapter of an objcopy machine name (`arm`); an unknown machine is refused before connecting."""
    machine = machine or DEFAULT_MACHINE
    if machine not in ADAPTERS:
        raise ValueError(f"Unsupported target architecture: {machine}")
    return ADAPTERS[machine]
