import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from stm32_gdbtest.image import parse_sections, validate_regions, compare_regions
from stm32_gdbtest.runner import execute, ROOT

BASE = 0x08000000
SECTIONS = """
Sections:
Idx Name          Size      VMA       LMA       File off  Algn
  0 .text         00000004  08000000  08000000  00001000  2**2
                  CONTENTS, ALLOC, LOAD, READONLY, CODE
  1 .data         00000004  20000000  08000010  00002000  2**2
                  CONTENTS, ALLOC, LOAD, DATA
  2 .bss          00000008  20000004  08000014  00002004  2**2
                  ALLOC
  3 .debug_info   00000004  00000000  00000000  00002004  2**0
                  CONTENTS, READONLY, DEBUGGING, OCTETS
"""


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.regions = parse_sections(SECTIONS, BASE, 64)
        self.image = b"code" + b"\xff" * 12 + b"data"

    def test_lma_not_ram_vma_and_skip_bss_debug(self):
        self.assertEqual([r["name"] for r in self.regions], [".text", ".data"])
        self.assertEqual(self.regions[1]["address"], BASE + 16)
        self.assertEqual(validate_regions(self.regions, BASE, 64, 20), 20)

    def test_unprogrammed_gap_never_read_even_when_different(self):
        flash = b"code" + b"\xa5" * 12 + b"data"
        calls = []
        def read(address, size):
            calls.append((address, size))
            return flash[address - BASE:address - BASE + size]
        results = compare_regions(read, self.image, self.regions, BASE, 64)
        self.assertTrue(all(r["matches"] for r in results))
        self.assertEqual(calls, [(BASE, 4), (BASE + 16, 4)])
        self.assertNotEqual(flash, self.image)

    def test_payload_difference_is_detected(self):
        flash = b"code" + b"\xff" * 12 + b"bad!"
        results = compare_regions(lambda a, n: flash[a-BASE:a-BASE+n], self.image,
                                  self.regions, BASE, 64)
        self.assertEqual([r["matches"] for r in results], [True, False])

    def test_invalid_extents_rejected_without_memory_access(self):
        variants = [[], [dict(name="x", address=BASE-1, size=4, offset=-1)],
                    [dict(name="x", address=BASE, size=65, offset=0)],
                    [dict(name="x", address=BASE, size=0, offset=0)],
                    [dict(name="x", address=BASE, size=4, offset=1)],
                    [dict(name="x", address=BASE+4, size=4, offset=4)],
                    self.regions[::-1], self.regions + self.regions,
                    [dict(name="x", address=BASE, size=True, offset=0)]]
        def forbidden(*args):
            self.fail("Must reject before memory access")
        for regions in variants:
            with self.subTest(regions=regions), self.assertRaises(ValueError):
                compare_regions(forbidden, self.image, regions, BASE, 64)

    def test_ram_lma_and_out_of_bounds_are_rejected(self):
        for text in (SECTIONS.replace("08000010", "20000000"),
                     SECTIONS.replace("08000010", "08000040")):
            with self.assertRaises(ValueError):
                parse_sections(text, BASE, 64)

    def test_no_load_sections_or_malformed_output_rejected(self):
        for text in ("", SECTIONS.replace("CONTENTS, ALLOC, LOAD", "ALLOC"),
                     SECTIONS.replace("00000004  08000000", "not-hex  08000000"),
                     SECTIONS.replace("CONTENTS, ALLOC, LOAD, DATA", "unexpected flags")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_sections(text, BASE, 64)

    def test_bin_extent_mismatch_rejected(self):
        for size in (0, 19, 21, 65):
            with self.assertRaises(ValueError):
                validate_regions(self.regions, BASE, 64, size)

    def test_chunked_reads_and_short_read_errors(self):
        region = [dict(name="large", address=BASE, size=9000, offset=0)]
        sizes = []
        def read(address, size):
            sizes.append(size)
            return b"\xff" * size
        self.assertTrue(compare_regions(read, b"\xff"*9000, region, BASE, 9000)[0]["matches"])
        self.assertEqual(sizes, [4096, 4096, 808])
        with self.assertRaisesRegex(RuntimeError, "Short"):
            compare_regions(lambda a,n: b"", self.image, self.regions, BASE, 64)
        def unreadable(*args):
            raise OSError("unreadable")
        with self.assertRaises(OSError):
            compare_regions(unreadable, self.image, self.regions, BASE, 64)

    def test_invalid_elf_layout_stops_before_objcopy_gdb_or_server(self):
        parent = ROOT / "build/image-tests"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root = Path(temp)
            elf = root / "input.elf"
            elf.write_bytes(b"fixture; objdump is mocked")
            out = root / "run"
            out.mkdir()
            session = dict(root=str(root), elf=str(elf), profile=str(root / "target.toml"), gdb="unused.exe")
            report = {}
            with patch("stm32_gdbtest.runner.subprocess.check_output",
                       return_value=SECTIONS.replace("08000010", "20000000").encode()), \
                 patch("stm32_gdbtest.runner.subprocess.run") as run, \
                 patch("stm32_gdbtest.runner.subprocess.Popen") as popen:
                execute(session, {}, {}, out, report, 10, dict(flash_start=BASE, flash_size=64))
            run.assert_not_called()
            popen.assert_not_called()
            self.assertEqual(report["status"], "ERROR")
            self.assertIn("outside profile Flash", report["error"])
