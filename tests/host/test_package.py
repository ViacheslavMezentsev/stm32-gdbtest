"""Prepared run packages without a toolchain or a debugger (TC-104…TC-106, TC-116)."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from stm32_gdbtest.package import MANIFEST, open_package, pack

SCENARIO = '''from stm32_gdbtest import case


@case("HW_ONE", timeout_s=5, labels=("gpio",))
def one(t):
    t.reach("main")


@case("HW_TWO")
def two(t):
    t.reach("main")
'''


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = self.root = Path(self.temp.name) / "project"
        board = root / "profile/Tests/board"
        board.mkdir(parents=True)
        (board / "test_one.py").write_text(SCENARIO)
        (root / "profile/Tests/contracts.json").write_text('{"schema": 1, "contracts": {}}')
        (root / "profile/target.toml").write_bytes(b"[mcu]\r\nname = 'x'\r\n")  # CRLF kept byte for byte
        (root / "helpers").mkdir()
        (root / "helpers/steps.py").write_text("VALUE = 1\n")
        (root / "build").mkdir()
        (root / "build/fw.elf").write_bytes(b"\x7fELF" + bytes(range(64)))
        (root / "build/manifest.json").write_text("{}")
        self.session = dict(root=str(root), elf=str(root / "build/fw.elf"), profile=str(root / "profile/target.toml"),
                            tests=str(board), build_manifest=str(root / "build/manifest.json"), out=str(root / "runs"))
        self.output = Path(self.temp.name) / "out/pkg.zip"
        self.gdb = Path(self.temp.name) / "gdb"
        self.gdb.write_text("")

    def test_pack_and_open_verify_every_file(self):
        # TC-104: ТЗ 5.19.1–5.19.3
        prepared = []
        manifest = pack(self.session, self.output, include=["helpers"], prepare=lambda t: prepared.append(t["id"]) or "PASS")
        self.assertEqual(prepared, ["HW_ONE", "HW_TWO"])
        self.assertEqual(manifest["prepared"], {"HW_ONE": "PASS", "HW_TWO": "PASS"})
        with zipfile.ZipFile(self.output) as bundle:
            self.assertEqual(sorted(bundle.namelist()), sorted([MANIFEST, "firmware.elf", "build-manifest.json",
                "profile/target.toml", "profile/tests/board/test_one.py", "profile/tests/contracts.json",
                "helpers/steps.py"]))
        session = open_package(self.output, Path(self.temp.name) / "work", str(self.gdb))
        extracted = Path(session["root"])
        self.assertEqual((extracted / "profile/target.toml").read_bytes(), b"[mcu]\r\nname = 'x'\r\n")
        self.assertEqual(session["tests"], str(extracted / "profile/tests/board"))
        self.assertEqual(session["gdb"], str(self.gdb))
        self.assertEqual(session["package"]["prepared"]["HW_ONE"], "PASS")
        self.assertTrue((extracted / "helpers/steps.py").is_file())
        only = pack(self.session, self.output, test_ids=["HW_TWO"])
        self.assertEqual([t["id"] for t in only["tests"]], ["HW_TWO"])

    def test_reopen_preserves_reports_and_uses_clean_sources(self):
        # TC-133: ТЗ 5.19.5 — successful and failed opens preserve earlier evidence.
        pack(self.session, self.output)
        work = Path(self.temp.name) / "work"
        first = open_package(self.output, work, str(self.gdb))
        runs = Path(first["out"])
        evidence = runs / "previous" / "result.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_bytes(b'{"status":"ERROR"}')
        original_elf = Path(first["elf"]).read_bytes()
        Path(first["elf"]).write_bytes(b"changed during previous run")
        (Path(first["root"]) / "unexpected.py").write_text("stale = True")
        second = open_package(self.output, work, str(self.gdb))
        self.assertNotEqual(first["out"], second["out"])
        self.assertTrue(Path(second["out"]).is_relative_to(Path(second["root"])))
        self.assertNotEqual(first["root"], second["root"])
        self.assertEqual(evidence.read_bytes(), b'{"status":"ERROR"}')
        self.assertEqual(Path(second["elf"]).read_bytes(), original_elf)
        self.assertFalse((Path(second["root"]) / "unexpected.py").exists())
        with patch("stm32_gdbtest.package.find_gdb", return_value=None):
            with self.assertRaises(FileNotFoundError):
                open_package(self.output, work)
        self.assertEqual(evidence.read_bytes(), b'{"status":"ERROR"}')
        self.assertEqual(Path(second["elf"]).read_bytes(), original_elf)

    def test_legacy_uppercase_package_still_opens(self):
        # TC-128: schema1 archives retain their manifest-declared path spelling.
        pack(self.session, self.output)
        with zipfile.ZipFile(self.output) as bundle:
            entries = {name.replace("profile/tests/", "profile/Tests/"): bundle.read(name)
                       for name in bundle.namelist()}
        manifest = json.loads(entries[MANIFEST])
        manifest["tests_dir"] = "profile/Tests/board"
        manifest["files"] = {name.replace("profile/tests/", "profile/Tests/"): digest
                             for name, digest in manifest["files"].items()}
        entries[MANIFEST] = json.dumps(manifest).encode()
        legacy = Path(self.temp.name) / "legacy.zip"
        with zipfile.ZipFile(legacy, "w") as bundle:
            for name, data in entries.items():
                bundle.writestr(name, data)
        opened = open_package(legacy, Path(self.temp.name) / "legacy-work", str(self.gdb))
        self.assertEqual(Path(opened["tests"]).parent.name, "Tests")
        self.assertTrue((Path(opened["tests"]) / "test_one.py").is_file())

    def test_changed_extra_or_unsafe_entries_are_refused(self):
        # TC-105: ТЗ 5.19.3
        pack(self.session, self.output)
        work = Path(self.temp.name) / "work"
        with zipfile.ZipFile(self.output) as bundle:
            entries = {name: bundle.read(name) for name in bundle.namelist()}
        for change, message in ((lambda e: e.update({"firmware.elf": b"other"}), "changed"),
                                (lambda e: e.update({"extra.py": b""}), "do not match"),
                                (lambda e: e.update({"../evil": b""}), "do not match")):
            broken = dict(entries)
            change(broken)
            path = Path(self.temp.name) / "broken.zip"
            with zipfile.ZipFile(path, "w") as bundle:
                for name, data in broken.items():
                    bundle.writestr(name, data)
            with self.assertRaisesRegex(ValueError, message):
                open_package(path, work, str(self.gdb))
        manifest = json.loads(entries[MANIFEST])
        manifest["files"]["../evil"] = "0" * 64
        path = Path(self.temp.name) / "unsafe.zip"
        with zipfile.ZipFile(path, "w") as bundle:
            for name, data in dict(entries, **{MANIFEST: json.dumps(manifest).encode(), "../evil": b""}).items():
                bundle.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "do not match"):
            open_package(path, work, str(self.gdb))
        with patch.dict(os.environ, {"STM32_GDBTEST_GDB": "", "ARM_TOOLCHAIN_ROOT": "", "USERPROFILE": ""}), \
                patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "GDB"):
                open_package(self.output, work)

    def test_pack_refuses_failed_preparation_and_bad_input(self):
        # TC-106: ТЗ 5.19.2
        with self.assertRaisesRegex(RuntimeError, "HW_TWO"):
            pack(self.session, self.output, prepare=lambda t: "PASS" if t["id"] == "HW_ONE" else "ERROR")
        self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError, "Unknown scenario"):
            pack(self.session, self.output, test_ids=["HW_NONE"])
        with self.assertRaisesRegex(ValueError, "inside the project root"):
            pack(self.session, self.output, include=["../outside"])

    def test_target_description_outside_the_scenario_directory(self):
        # TC-116: ТЗ 5.13.2, 5.19.1 — one Tests/ for several MCU variants, target.toml elsewhere
        variant = self.root / "profiles/g431.toml"
        variant.parent.mkdir()
        variant.write_bytes(b"[mcu]\nname = 'g431'\n")
        session = dict(self.session, profile=str(variant))
        manifest = pack(session, self.output)
        self.assertEqual(manifest["tests_dir"], "profile/tests/board")
        with zipfile.ZipFile(self.output) as bundle:
            self.assertEqual(bundle.read("profile/target.toml"), b"[mcu]\nname = 'g431'\n")
            self.assertIn("profile/tests/contracts.json", bundle.namelist())
        opened = open_package(self.output, Path(self.temp.name) / "work", str(self.gdb))
        self.assertEqual(Path(opened["tests"]).parent, Path(opened["profile"]).parent / "tests")


if __name__ == "__main__":
    unittest.main()
