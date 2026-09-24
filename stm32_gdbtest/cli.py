"""Host CLI; collection and traceability never import gdb or test modules."""

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest import __version__
from stm32_gdbtest.collect import collect, trace


def main():
    parser = argparse.ArgumentParser(prog="stm32-gdbtest")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    subs = parser.add_subparsers(dest="command", required=True)
    gather = subs.add_parser("collect")
    gather.add_argument("--tests", type=Path, required=True)
    gather.add_argument("--cmake", type=Path)
    gather.add_argument("--workspace", type=Path, default=ROOT)
    check = subs.add_parser("trace")
    check.add_argument("--tests", type=Path, required=True)
    check.add_argument("--requirements", type=Path, required=True)
    run_parser = subs.add_parser("run")
    run_parser.add_argument("--session", type=Path, required=True)
    run_parser.add_argument("--test", required=True)
    run_parser.add_argument("--stand", type=Path)
    run_parser.add_argument("--timeout", type=float)
    run_parser.add_argument("--identity-policy", choices=("warn", "strict"))
    run_parser.add_argument("--image-policy", type=Path)
    args = parser.parse_args()
    if args.command == "collect":
        tests = collect(args.tests)
        if args.cmake:
            from stm32_gdbtest.runner import local_directory
            local_directory(args.cmake.resolve().parent, args.workspace)
            args.cmake.write_text("\n".join(
                f"stm32_gdbtest_register({t['id']} {t['timeout_s']} \"{';'.join(t['labels'])}\")"
                for t in tests) + "\n", encoding="utf-8")
        else:
            print(json.dumps(tests, indent=2))
        return 0
    if args.command == "trace":
        trace(collect(args.tests), args.requirements)
        print("Requirement IDs and tests match")
        return 0
    from stm32_gdbtest.runner import run
    session = json.loads(args.session.read_text(encoding="utf-8"))
    tests = {t["id"]: t for t in collect(session["tests"])}
    return run(session, tests[args.test], args.stand, args.timeout, args.identity_policy, args.image_policy)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
