"""Transport roundtrip and corruption checks, independent of GDB/hardware."""

import base64
from datetime import date, datetime, time
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from config_transport import dumps, loads, open_config, pack_config
from session_config import ConfigError, load_session
from test_session_config import TARGET


API = '''schema=1
[records]
max_records=7
[custom]
date=2026-10-03
local=2026-10-03T12:34:56.123456
offset=2026-10-03T12:34:56+05:00
time=12:34:56.123456
positive=inf
negative=-inf
nan=nan
zero=-0.0
integer=9223372036854775807
array=[{text="значение", flags=[true,false]}, 2]
'''


class TransportTests(unittest.TestCase):
    def snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.toml").write_bytes(TARGET.encode())
            (root / "api.toml").write_bytes(API.encode())
            (root / "session.toml").write_text(
                '[config]\ntarget="target.toml"\napi="api.toml"', encoding="utf-8")
            result = load_session(root / "session.toml", environ={})
        # Original paths no longer exist before any receiving-side operation.
        return result

    def test_json_roundtrip_all_toml_scalar_types(self):
        original = self.snapshot()
        received = loads(dumps(original))
        values = received.config["api"]["custom"]
        self.assertIs(type(values["date"]), date)
        self.assertIs(type(values["local"]), datetime)
        self.assertIsNone(values["local"].tzinfo)
        self.assertEqual(values["offset"].utcoffset().total_seconds(), 18000)
        self.assertIs(type(values["time"]), time)
        self.assertEqual(values["time"].microsecond, 123456)
        self.assertEqual(values["positive"], math.inf)
        self.assertEqual(values["negative"], -math.inf)
        self.assertTrue(math.isnan(values["nan"]))
        self.assertEqual(math.copysign(1, values["zero"]), -1)
        self.assertEqual(values["integer"], 9223372036854775807)
        self.assertEqual(values["array"][0]["text"], "значение")
        self.assertEqual(values["array"][0]["flags"], (True, False))
        self.assertEqual(received.config_props["api"]["sha256"], original.config_props["api"]["sha256"])
        self.assertNotIn("max_depth", received.config_props["api"]["data"]["records"])
        self.assertEqual(received.config["api"]["records"]["max_depth"], 8)
        with self.assertRaises(TypeError):
            values["array"][0]["text"] = "changed"

    def test_config_archive_without_original_sources(self):
        snapshot = self.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "config.zip"
            pack_config(snapshot, archive)
            restored = open_config(archive)
        self.assertEqual(restored.config["api"]["records"]["max_records"], 7)
        self.assertEqual(restored.config_props["api"]["reference"], "api.toml")
        self.assertEqual(restored.session_sha256, snapshot.session_sha256)

    def test_hash_schema_defaults_and_file_set_corruption(self):
        original = dumps(self.snapshot())
        for kind in ("hash", "schema", "defaults", "missing", "extra", "base64"):
            data = json.loads(original)
            if kind == "hash": data["files"]["api"]["sha256"] = "0" * 64
            if kind == "schema": data["schema"] = True
            if kind == "defaults": data["defaults"] = "other version"
            if kind == "missing": del data["files"]["api"]
            if kind == "extra": data["files"]["unused"] = data["files"]["api"]
            if kind == "base64": data["files"]["api"]["base64"] = "!invalid!"
            with self.subTest(kind=kind), self.assertRaises(ConfigError):
                loads(json.dumps(data))

    def test_revalidates_data_even_with_updated_hash(self):
        data = json.loads(dumps(self.snapshot()))
        raw = API.replace('max_records=7', 'max_records=-1').encode()
        data["files"]["api"] = dict(base64=base64.b64encode(raw).decode(),
                                      sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ConfigError):
            loads(json.dumps(data))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ConfigError):
            loads('{"schema":1,"schema":1}')


if __name__ == "__main__":
    unittest.main()
