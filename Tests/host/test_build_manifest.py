import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stm32_gdbtest.build_manifest import dependency_map, digest, label, load_verified, selected_flags, version_macros
from stm32_gdbtest.runner import ROOT, execute


class BuildManifestTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / "build/host-tests"
        directory.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.profile = self.directory / "target.toml"
        self.profile.write_text("profile")
        self.elf = self.directory / "firmware.elf"
        self.elf.write_bytes(b"ELF fixture")
        self.manifest = self.directory / "manifest.json"
        self.data = dict(schema=1, elf_sha256=digest(self.elf), profile_sha256=digest(self.profile),
                         compilers=[{}], units=[{}], inputs=[{}], library_versions=[{}], cube_packages=["F1"])
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.data))

    def test_mismatched_artifacts_and_incomplete_schema_are_rejected(self):
        for key, value in (("schema", True), ("schema", 2), ("elf_sha256", "stale"),
                           ("profile_sha256", "stale"), ("units", [])):
            with self.subTest(key=key, value=value):
                changed = dict(self.data, **{key: value})
                self.manifest.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    load_verified(self.manifest, digest(self.elf), self.profile)
        self.manifest.unlink()
        with self.assertRaises(FileNotFoundError):
            load_verified(self.manifest, digest(self.elf), self.profile)

    def test_runtime_uses_snapshot_without_rereading_build_sources(self):
        self.data["inputs"] = [{"file": "missing/source.c", "sha256": "historical"}]
        self.save()
        self.assertEqual(load_verified(self.manifest, digest(self.elf), self.profile), self.data)
        self.profile.write_text("changed profile")
        with self.assertRaisesRegex(ValueError, "target profile"):
            load_verified(self.manifest, digest(self.elf), self.profile)

    def test_invalid_manifest_stops_runner_before_any_process_start(self):
        self.data["elf_sha256"] = "stale"
        self.save()
        out = self.directory / "run"
        out.mkdir()
        session = dict(elf=str(self.elf), profile=str(self.profile), gdb="unused.exe",
                       build_manifest=str(self.manifest))
        report = {}
        with patch("stm32_gdbtest.runner.subprocess.run") as run, patch("stm32_gdbtest.runner.subprocess.Popen") as popen:
            execute(session, {}, {}, out, report, 10, {})
        run.assert_not_called()
        popen.assert_not_called()
        self.assertEqual(report["status"], "ERROR")
        self.assertIn("does not match ELF", report["error"])
        self.assertFalse((out / "server.log").exists())

    def test_dependency_parser_preserves_spaces_and_stale_state(self):
        text = "obj file.obj: #deps 1, deps mtime 123 (VALID)\n    C:/directory with spaces/a.h\nother.obj: #deps 1, deps mtime 123 (STALE)\n    stale.h\n"
        result = dependency_map(text, self.directory)
        self.assertEqual(result[self.directory / "obj file.obj"], [Path("C:/directory with spaces/a.h").resolve()])
        self.assertIsNone(result[self.directory / "other.obj"])

    def test_versions_are_literal_declarations_not_macro_evaluation(self):
        text = "#define __STM32F1xx_HAL_VERSION_MAIN (0x01U) /* comment */\n#define __CM_CMSIS_VERSION_SUB (1U)\n#define __CM_CMSIS_VERSION_MAIN (1 + 5)\n"
        self.assertEqual(version_macros(text.replace("\n", "\r\n")), {"__STM32F1xx_HAL_VERSION_MAIN": 1, "__CM_CMSIS_VERSION_SUB": 1})

    def test_display_metadata_does_not_copy_installation_paths(self):
        flags = selected_flags(["-Og", "-g3", "-mcpu=cortex-m3", "-IC:/Users/PRIVATE", '-DHOME="C:/PRIVATE"'])
        self.assertEqual(flags, ["-Og", "-g3", "-mcpu=cortex-m3"])
        self.assertEqual(label(Path("C:/PRIVATE/STM32Cube_FW_F1_V1.8.7/header.h"), ROOT),
                         "STM32Cube_FW_F1_V1.8.7/header.h")
        self.assertEqual(label(Path("C:/PRIVATE/header.h"), ROOT), "external/header.h")
