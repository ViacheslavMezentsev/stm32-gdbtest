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


def read_named_register(frame, name):
    """Value and GDB name of a diagnostic register.

    The name comes from the profile; the GDB server's target description may spell it differently
    (`xPSR` on OpenOCD 0.12.0, `xpsr` on the xPack OpenOCD build). If the exact name fails, the one
    register of the frame architecture whose name differs only in letter case is read instead;
    otherwise the original error is raised. The value is masked by the register width, so a signed
    32-bit type in the target description does not turn a set bit 31 into a negative number.
    """
    try:
        return _unsigned(frame.read_register(name)), name
    except Exception as exact:
        try:
            names = [register.name for register in frame.architecture().registers()]
        except Exception:
            raise exact from None
        matches = sorted({other for other in names if other != name and other.lower() == name.lower()})
        if len(matches) != 1:
            raise exact
        return _unsigned(frame.read_register(matches[0])), matches[0]


def _unsigned(value):
    size = getattr(getattr(value, "type", None), "sizeof", None)
    number = int(value)
    return number & ((1 << (8 * int(size))) - 1) if size else number


ADAPTERS = {"arm": CortexM()}
DEFAULT_MACHINE = "arm"


def adapter(machine):
    """Adapter of an objcopy machine name (`arm`); an unknown machine is refused before connecting."""
    machine = machine or DEFAULT_MACHINE
    if machine not in ADAPTERS:
        raise ValueError(f"Unsupported target architecture: {machine}")
    return ADAPTERS[machine]
