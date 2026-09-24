"""STM32 runtime testing through GDB-Python; host-safe public metadata API."""
import sys

# Source checkouts may be read-only, including GDB imports and the -m entry point.
sys.dont_write_bytecode = True
__version__ = "0.1.0.dev0"
API_VERSION = 1
__all__ = ["case", "API_VERSION", "__version__"]


def case(identifier, *, timeout_s=20, labels=(), contracts=()):
    """Metadata is read statically by the host; GDB imports the function unchanged."""
    def decorate(function):
        return function
    return decorate
