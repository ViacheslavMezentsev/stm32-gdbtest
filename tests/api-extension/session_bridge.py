"""Research bridge for CMake selection and JSON preparation; never starts GDB."""

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config_transport import dumps
from session_config import ConfigError, load_session


def select(path):
    snapshot = load_session(path)
    return (Path(path).resolve().parent / snapshot.config_props["target"]["reference"]).resolve()


def prepare(session, *, image_policy=None, environ=None):
    """Return unchanged legacy descriptor, or new descriptor plus capsule.

    This checks profile selection, not ELF/build-manifest validity; production
    runner checks remain mandatory and are tested separately from this bridge.
    """
    if "session_config" not in session:
        return dict(session), None
    path = Path(session["session_config"])
    snapshot = load_session(path, image_policy=image_policy, environ=environ)
    selected = (path.resolve().parent / snapshot.config_props["target"]["reference"]).resolve()
    if Path(session["profile"]).resolve() != selected:
        raise ConfigError("stale_selection", "regenerate CMake session after changing target selection")
    return dict(session), dumps(snapshot)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--select", type=Path)
    args = parser.parse_args()
    if args.select is None:
        parser.error("--select required")
    print(select(args.select).as_posix())


if __name__ == "__main__":
    main()
