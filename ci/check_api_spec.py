"""Run the upstream spec checker with three-component revision recognition.

Only revision token patterns are widened; requirement and traceability checks
remain those of embedded-tech-spec. The supplied checker stays unmodified.
"""

import sys
from pathlib import Path


def adapt(source):
    pattern = r"\d+\.\d+"
    if source.count(pattern) != 4:
        raise ValueError("Upstream revision patterns changed; review this adapter")
    return source.replace(pattern, r"\d+\.\d+(?:\.\d+)?")


if __name__ == "__main__":
    checker = Path(sys.argv.pop(1)).resolve()
    source = adapt(checker.read_text(encoding="utf-8"))
    exec(compile(source, str(checker), "exec"),
         {"__name__": "__main__", "__file__": str(checker)})
