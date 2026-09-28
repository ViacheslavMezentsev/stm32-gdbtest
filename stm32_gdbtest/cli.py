"""Host CLI; collection and traceability never import gdb or test modules."""

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if sys.version_info < (3, 11):
    # ТЗ 2.5.2: the runner needs tomllib; on Linux stands the system Python is older.
    sys.exit(f"stm32-gdbtest needs Python 3.11+, this is {sys.version.split()[0]} ({sys.executable}). "
             "On a Linux stand run: . ~/.local/stm32-gdbtest/env.sh")
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
    source = run_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--session", type=Path)
    source.add_argument("--package", type=Path, help="prepared run package created by `pack`")
    run_parser.add_argument("--gdb", type=Path, help="GDB with Python for --package (default: lookup)")
    run_parser.add_argument("--workdir", type=Path, default=Path("build/ddtt-packages"),
                            help="where --package is verified and extracted")
    run_parser.add_argument("--test", required=True)
    run_parser.add_argument("--stand", type=Path)
    run_parser.add_argument("--timeout", type=float)
    run_parser.add_argument("--identity-policy", choices=("warn", "strict"))
    run_parser.add_argument("--image-policy", type=Path)
    run_parser.add_argument("--prepare-only", action="store_true",
                            help="run every host-side step before the GDB server, without hardware access")
    packer = subs.add_parser("pack", help="prepare scenarios here and write a package to run on a stand")
    packer.add_argument("--session", type=Path, required=True)
    packer.add_argument("--output", type=Path, required=True, help="package file, *.zip")
    packer.add_argument("--test", action="append", help="scenario ID; repeat; default: all")
    packer.add_argument("--include", action="append", default=[],
                        help="helper file or directory relative to the project root; repeat")
    doctor = subs.add_parser("doctor", help="check GDB-Python, binutils, tools, stand and USB access")
    doctor.add_argument("--gdb", type=Path)
    doctor.add_argument("--stand", type=Path)
    doctor.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.command == "doctor":
        from stm32_gdbtest.doctor import main as doctor_main
        return doctor_main(args.gdb, args.stand, args.json)
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
    if args.command == "pack":
        from stm32_gdbtest.package import pack
        session = json.loads(args.session.read_text(encoding="utf-8"))
        try:
            manifest = pack(session, args.output, args.test, args.include,
                            prepare=lambda test: "PASS" if run(session, test, prepare_only=True) == 0 else "ERROR")
        except RuntimeError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(f"Package {args.output}: {len(manifest['tests'])} scenarios, ELF {manifest['elf_sha256'][:12]}")
        return 0
    if args.package:
        from stm32_gdbtest.package import open_package
        session = open_package(args.package, args.workdir, args.gdb and str(args.gdb))
    else:
        session = json.loads(args.session.read_text(encoding="utf-8"))
    tests = {t["id"]: t for t in collect(session["tests"])}
    return run(session, tests[args.test], args.stand, args.timeout, args.identity_policy, args.image_policy,
               args.prepare_only)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
