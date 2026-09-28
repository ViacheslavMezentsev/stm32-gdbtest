"""Prepared run packages without a toolchain or a debugger (TC-104…TC-106)."""
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
                "profile/target.toml", "profile/Tests/board/test_one.py", "profile/Tests/contracts.json",
                "helpers/steps.py"]))
        session = open_package(self.output, Path(self.temp.name) / "work", str(self.gdb))
        extracted = Path(session["root"])
        self.assertEqual((extracted / "profile/target.toml").read_bytes(), b"[mcu]\r\nname = 'x'\r\n")
        self.assertEqual(session["tests"], str(extracted / "profile/Tests/board"))
        self.assertEqual(session["gdb"], str(self.gdb))
        self.assertEqual(session["package"]["prepared"]["HW_ONE"], "PASS")
        self.assertTrue((extracted / "helpers/steps.py").is_file())
        only = pack(self.session, self.output, test_ids=["HW_TWO"])
        self.assertEqual([t["id"] for t in only["tests"]], ["HW_TWO"])

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
        outside = dict(self.session, tests=str(self.root / "helpers"))
        (self.root / "helpers/test_x.py").write_text(SCENARIO)
        with self.assertRaisesRegex(ValueError, "inside the profile directory"):
            pack(outside, self.output)


if __name__ == "__main__":
    unittest.main()
