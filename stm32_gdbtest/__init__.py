"""STM32 runtime testing through GDB-Python; host-safe public metadata API."""
import sys

from stm32_gdbtest.errors import ApiError, CheckFailed, RecordError
from stm32_gdbtest.matchers import matches, near, one_of, within

# Source checkouts may be read-only, including GDB imports and the -m entry point.
sys.dont_write_bytecode = True
__version__ = "0.4.1"
API_VERSION = 2
__all__ = ["case", "test", "within", "near", "one_of", "matches", "API_VERSION", "__version__", "ApiError", "CheckFailed",
           "RecordError"]


def case(identifier, *, timeout_s=20, labels=(), contracts=()):
    """Metadata is read statically by the host; GDB imports the function unchanged."""
    def decorate(function):
        return function
    return decorate


def test(identifier, *, timeout_s=20, labels=(), contracts=()):
    """Alias of `case` under the name used by the 0.3.0 package (ТЗ API 4.2)."""
    return case(identifier, timeout_s=timeout_s, labels=labels, contracts=contracts)
