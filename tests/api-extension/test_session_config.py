"""Independent file fixtures for the research configuration loader."""

from datetime import date, datetime, time
import hashlib
from pathlib import Path
import tempfile
import unittest

from session_config import ConfigError, load_session


TARGET = '''schema=1
name="example"
mcu="STM32F411CEU6"
openocd_target="target/stm32f4x.cfg"
flash_start=0x08000000
flash_size=524288
breakpoint_limit=6
fault_handlers=["HardFault_Handler"]
core_registers=["pc", "sp"]
reset_halt="monitor reset halt"
reset_run="monitor reset run"
[identity]
address=0xE0042000
mask=0xFFF
value=0x431
[diagnostic_registers]
CFSR=0xE000ED28
'''
IMAGE = '''[image]
schema=1
mode="full"
start=0x08000000
end=0x08004000
fill=255
crc="crc32-iso-hdlc"
'''


class SessionConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("target.toml", TARGET)
        self.write("full_image.toml", IMAGE)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def load(self, links='target="target.toml"', **kwargs):
        path = self.write("session.toml", "[config]\n" + links)
        return load_session(path, environ={}, **kwargs)

    def test_optional_files_and_defaults(self):
        result = self.load()
        self.assertIsNone(result.config_props["api"])
        self.assertIsNone(result.config_props["image"])
        self.assertIsNone(result.config["image"])
        self.assertEqual(result.config["api"]["records"]["max_records"], 128)

    def test_override_unknown_content_and_source_hash(self):
        path = self.write("api.toml", 'schema=1\n[records]\nmax_records=17\nnote="sample"\n'
                          '[measurement]\nsamples=[2,3]\nvdda_min_mv=3200\n')
        raw = path.read_bytes()
        r = self.load('target="target.toml"\napi="api.toml"\nimage="full_image.toml"')
        self.assertEqual(r.config["api"]["records"]["max_records"], 17)
        self.assertEqual(r.config["api"]["records"]["max_depth"], 8)
        self.assertEqual(r.config["api"]["records"]["note"], "sample")
        self.assertEqual(r.config["api"]["measurement"]["samples"], (2, 3))
        self.assertNotIn("max_depth", r.config_props["api"]["data"]["records"])
        self.assertEqual(r.config_props["api"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(r.config_props["api"]["reference"], "api.toml")
        self.assertEqual(r.config["image"]["image"]["end"], 0x08004000)

    def test_nested_immutability_and_isolation(self):
        self.write("api.toml", 'schema=1\n[custom]\nvalues=[{x=1}]\n')
        r = self.load('target="target.toml"\napi="api.toml"')
        for view in (r.config["api"], r.config_props["api"]["data"]):
            with self.assertRaises(TypeError):
                view["custom"]["values"][0]["x"] = 2
        with self.assertRaises(TypeError):
            r.config_props["api"]["reference"] = "other.toml"
        self.write("api.toml", 'schema=1\n[custom]\nvalues=[{x=9}]\n')
        other = self.load('target="target.toml"\napi="api.toml"')
        self.assertEqual(r.config["api"]["custom"]["values"][0]["x"], 1)
        self.assertEqual(other.config["api"]["custom"]["values"][0]["x"], 9)

    def test_selected_paths_relative_to_session(self):
        self.write("nested/target.toml", TARGET.replace('name="example"', 'name="nested"'))
        session = self.write("nested/session.toml", '[config]\ntarget="target.toml"')
        r = load_session(session, environ={})
        self.assertEqual(r.config["target"]["name"], "nested")

    def test_single_read_and_changes_after_capture(self):
        counts = {}
        expected_bytes = (self.root / "target.toml").read_bytes()
        def reader(path):
            counts[path.name] = counts.get(path.name, 0) + 1
            raw = path.read_bytes()
            if path.name == "target.toml":
                path.write_text("invalid TOML !", encoding="utf-8")
            return raw
        r = self.load(reader=reader)
        self.assertEqual(counts, {"session.toml": 1, "target.toml": 1})
        self.assertEqual(r.config["target"]["name"], "example")
        self.assertEqual(r.config_props["target"]["sha256"],
                         hashlib.sha256(expected_bytes).hexdigest())

    def test_known_parameter_types_and_ranges(self):
        for value in ('0', '-1', 'true', '1.5', '"12"', '[]'):
            with self.subTest(value=value):
                self.write("api.toml", 'schema=1\n[records]\nextra="allowed"\nmax_records='+value)
                with self.assertRaises(ConfigError) as caught:
                    self.load('target="target.toml"\napi="api.toml"')
                self.assertEqual(caught.exception.code, "api_parameter")

    def test_schema_and_known_table_shape(self):
        for text in ('[custom]\nx=1', 'schema=true', 'schema=2', 'schema="1"',
                     'schema=1\nrecords=2'):
            with self.subTest(text=text), self.assertRaises(ConfigError):
                self.write("api.toml", text)
                self.load('target="target.toml"\napi="api.toml"')

    def test_missing_or_invalid_references_do_not_fallback(self):
        for links in ('api="api.toml"', 'target="missing.toml"', 'target=""',
                      'target=1', 'target="target.toml"\napi="missing.toml"',
                      'target="target.toml"\nimage="missing.toml"'):
            with self.subTest(links=links), self.assertRaises(ConfigError):
                self.load(links)

    def test_invalid_toml_even_in_unknown_section(self):
        self.write("api.toml", 'schema=1\n[custom]\nx=1\nx=2')
        with self.assertRaises(ConfigError) as caught:
            self.load('target="target.toml"\napi="api.toml"')
        self.assertEqual(caught.exception.code, "source")

    def test_conflict_before_any_file_read(self):
        for options in (dict(profile="target.toml"), dict(image_policy="image.toml"),
                        dict(environ={"STM32_GDBTEST_IMAGE_POLICY": "image.toml"})):
            options.setdefault("environ", {})
            def forbidden(path):
                self.fail("conflict must be checked before reading")
            with self.subTest(options=options), self.assertRaises(ConfigError) as caught:
                load_session(self.root / "missing.toml", reader=forbidden, **options)
            self.assertEqual(caught.exception.code, "conflict")

    def test_target_and_image_validation(self):
        self.write("full_image.toml", IMAGE.replace('end=0x08004000', 'end=0x09000000'))
        with self.assertRaises(ConfigError) as caught:
            self.load('target="target.toml"\nimage="full_image.toml"')
        self.assertEqual(caught.exception.code, "image")
        self.write("target.toml", TARGET.replace('breakpoint_limit=6', 'breakpoint_limit=1'))
        with self.assertRaises(ConfigError) as caught:
            self.load()
        self.assertEqual(caught.exception.code, "target")

    def test_toml_dates_and_times_retained_locally(self):
        self.write("api.toml", 'schema=1\n[custom]\nday=2026-10-03\n'
                   'time=12:30:00\nstamp=2026-10-03T12:30:00Z\n')
        r = self.load('target="target.toml"\napi="api.toml"')
        custom = r.config["api"]["custom"]
        self.assertIs(type(custom["day"]), date)
        self.assertIs(type(custom["time"]), time)
        self.assertIs(type(custom["stamp"]), datetime)


if __name__ == "__main__":
    unittest.main()
