import binascii
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stm32_gdbtest.full_image import canonical_image, compare_full, load_policy, validate_image, validate_policy
from stm32_gdbtest.runner import execute, ROOT

BASE = 0x08000000
PROFILE = dict(flash_start=BASE, flash_size=128)
POLICY = dict(schema=1, mode="full", start=BASE, end=BASE+32, fill=255, crc="crc32-iso-hdlc")
REGIONS = [dict(name="text", address=BASE, size=4, offset=0),
           dict(name="data", address=BASE+16, size=4, offset=16)]
BINARY = b"code" + b"\x00"*12 + b"data"


class FullImageTests(unittest.TestCase):
    def test_canonical_padding_changes_gaps_and_tail_not_payload(self):
        self.assertEqual(canonical_image(BINARY, REGIONS, POLICY, PROFILE),
                         b"code" + b"\xff"*12 + b"data" + b"\xff"*12)
        alternate = canonical_image(BINARY, REGIONS, dict(POLICY, fill=0xa5), PROFILE)
        self.assertEqual(alternate, b"code" + b"\xa5"*12 + b"data" + b"\xa5"*12)
        validate_image(alternate, REGIONS, dict(POLICY, fill=0xa5), PROFILE)

    def test_unknown_keys_and_unsupported_schema_crc_are_rejected(self):
        for policy in [dict(POLICY, schema=True), dict(POLICY, schema=2), dict(POLICY, mode="typo"),
                       dict(POLICY, crc="stm32"), dict(POLICY, exclude=[0,4]), {}]:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                validate_policy(policy, PROFILE)

    def test_invalid_bounds_or_fill_rejected(self):
        for field, value in [("start", BASE+4), ("end", BASE), ("end", BASE+129),
                             ("end", True), ("fill", -1), ("fill", 256), ("fill", False)]:
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                validate_policy(dict(POLICY, **{field:value}), PROFILE)

    def test_payload_beyond_policy_rejected(self):
        with self.assertRaisesRegex(ValueError, "payload exceeds"):
            canonical_image(BINARY, REGIONS, dict(POLICY,end=BASE+19), PROFILE)

    def test_crc_known_vector_and_odd_length(self):
        data = b"123456789"
        policy = dict(POLICY, end=BASE+len(data))
        result = compare_full(lambda a,n: data[a-BASE:a-BASE+n], data, policy, PROFILE)
        self.assertEqual(result["crc"]["expected"], "0xCBF43926")
        self.assertEqual(result["crc"]["observed"], "0xCBF43926")
        self.assertTrue(result["full_region_crc_verified"])
        self.assertEqual(result["bytes_compared"], 9)

    def test_gap_tail_and_payload_corruption_detected(self):
        image = canonical_image(BINARY, REGIONS, POLICY, PROFILE)
        for index in (0, 7, 31):
            changed = bytearray(image)
            changed[index] ^= 1
            result = compare_full(lambda a,n: changed[a-BASE:a-BASE+n], image, POLICY, PROFILE)
            self.assertFalse(result["bytes_match"])
            self.assertFalse(result["full_region_crc_verified"])
            self.assertEqual(result["first_mismatch"], BASE+index)
            self.assertNotEqual(result["crc"]["expected"], result["crc"]["observed"])

    def test_byte_comparison_remains_required_even_with_equal_crc(self):
        with patch("stm32_gdbtest.full_image.binascii.crc32", return_value=123):
            r = compare_full(lambda a,n: b"x"*n, b"y"*32, POLICY, PROFILE)
        self.assertEqual(r["crc"]["expected"],r["crc"]["observed"])
        self.assertFalse(r["full_region_crc_verified"])

    def test_length_and_padding_checked_before_target_read(self):
        good = canonical_image(BINARY, REGIONS, POLICY, PROFILE)
        for image in (good[:-1], good+b"x", good[:8]+b"\x00"+good[9:]):
            with self.assertRaises(ValueError):
                validate_image(image, REGIONS, POLICY, PROFILE)
        with self.assertRaises(ValueError):
            compare_full(lambda a,n: self.fail("Must not read"), good[:-1], POLICY, PROFILE)

    def test_chunking_and_streaming_crc(self):
        data=bytes(range(256))*40+b"abc"
        policy=dict(POLICY,end=BASE+len(data))
        sizes=[]
        def read(a,n):
            sizes.append(n)
            return data[a-BASE:a-BASE+n]
        result=compare_full(read,data,policy,dict(PROFILE,flash_size=len(data)))
        self.assertEqual(sizes,[4096,4096,2051])
        self.assertEqual(result["crc"]["observed"], f"0x{binascii.crc32(data):08X}")

    def test_short_or_failed_read_is_error(self):
        with self.assertRaises(RuntimeError):
            compare_full(lambda a,n:b"",b"x"*32,POLICY,PROFILE)
        def fail(a,n):
            raise OSError("unreadable")
        with self.assertRaises(OSError):
            compare_full(fail,b"x"*32,POLICY,PROFILE)

    def test_bad_policy_stops_before_any_subprocess(self):
        parent=ROOT/"build/full-image-tests"
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            path=Path(temp)
            policy=path/"bad.toml"
            policy.write_text('[image]\nschema = 2\n')
            session=dict(root=str(path),gdb="unused",image_policy_path=str(policy))
            report={}
            with patch("stm32_gdbtest.runner.subprocess.run") as run, \
                 patch("stm32_gdbtest.runner.subprocess.check_output") as output, \
                 patch("stm32_gdbtest.runner.subprocess.Popen") as popen:
                execute(session,{}, {},path,report,10,PROFILE)
            for process in (run,output,popen): process.assert_not_called()
            self.assertEqual(report["status"],"ERROR")

    def test_policy_loader_rejects_other_tables_and_records_hash(self):
        parent=ROOT/"build/full-image-tests"
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            path=Path(temp)/"policy.toml"
            path.write_text('[image]\nschema=1\nmode="full"\nstart=0x08000000\n'
                            'end=0x08000020\nfill=255\ncrc="crc32-iso-hdlc"\n')
            policy,digest=load_policy(path,PROFILE)
            self.assertEqual(policy,POLICY)
            self.assertEqual(len(digest),64)
            path.write_text(path.read_text()+'\n[unknown]\n')
            with self.assertRaises(ValueError): load_policy(path,PROFILE)
