"""Source-checkout CLI: python -m stm32_gdbtest."""
import sys
from .cli import main

try:
    raise SystemExit(main())
except (ValueError, KeyError, OSError) as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    raise SystemExit(2)
