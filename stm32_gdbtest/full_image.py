"""Explicit full Flash image policy and CRC-32/ISO-HDLC readback on the host."""
import binascii
import hashlib
from pathlib import Path
import tomllib

from stm32_gdbtest.image import validate_regions


def validate_policy(policy, profile):
    required = {"schema", "mode", "start", "end", "fill", "crc"}
    if not isinstance(policy, dict) or set(policy) != required:
        raise ValueError("Full image policy must contain exactly schema/mode/start/end/fill/crc")
    if type(policy["schema"]) is not int or policy["schema"] != 1 or policy["mode"] != "full":
        raise ValueError("Unsupported image policy schema or mode")
    if any(type(policy[k]) is not int for k in ("start", "end", "fill")):
        raise ValueError("Image bounds and fill must be integers")
    if policy["start"] != profile["flash_start"] or not (
            policy["start"] < policy["end"] <= profile["flash_start"] + profile["flash_size"]):
        raise ValueError("Full image range must start at profile Flash and fit its bounds")
    if not 0 <= policy["fill"] <= 255 or policy["crc"] != "crc32-iso-hdlc":
        raise ValueError("Unsupported fill or CRC; use a byte and crc32-iso-hdlc")


def load_policy(path, profile):
    raw = Path(path).read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    if set(data) != {"image"}:
        raise ValueError("Expected only an [image] table")
    policy = data["image"]
    validate_policy(policy, profile)
    return policy, hashlib.sha256(raw).hexdigest()


def canonical_image(binary, regions, policy, profile):
    validate_policy(policy, profile)
    span = validate_regions(regions, profile["flash_start"], profile["flash_size"], len(binary))
    size = policy["end"] - policy["start"]
    if span > size:
        raise ValueError("ELF payload exceeds full image range")
    result = bytearray([policy["fill"]]) * size
    for region in regions:
        offset, count = region["offset"], region["size"]
        result[offset:offset + count] = binary[offset:offset + count]
    return bytes(result)


def validate_image(image, regions, policy, profile):
    validate_policy(policy, profile)
    span = validate_regions(regions, profile["flash_start"], profile["flash_size"])
    if len(image) != policy["end"] - policy["start"] or span > len(image):
        raise ValueError("Full BIN length or ELF extent differs from policy")
    # Reconstruct padding to reject accidental drift in gaps/tail before hardware access.
    if canonical_image(image[:span], regions, policy, profile) != image:
        raise ValueError("Full BIN padding differs from policy")


def compare_full(read_memory, image, policy, profile):
    validate_policy(policy, profile)
    if len(image) != policy["end"] - policy["start"]:
        raise ValueError("Full BIN length differs from policy")
    actual_crc = 0
    matches = True
    first_mismatch = None
    for offset in range(0, len(image), 4096):
        expected = image[offset:offset + 4096]
        actual = bytes(read_memory(policy["start"] + offset, len(expected)))
        if len(actual) != len(expected):
            raise RuntimeError("Short full-image Flash read")
        actual_crc = binascii.crc32(actual, actual_crc)
        if actual != expected:
            matches = False
            if first_mismatch is None:
                first_mismatch = policy["start"] + offset + next(
                    i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
    expected_crc = binascii.crc32(image)
    return dict(scope="full-image", start=policy["start"], end=policy["end"],
                fill=policy["fill"], bytes_compared=len(image), bytes_match=matches,
                first_mismatch=first_mismatch, gaps_verified=matches,
                full_region_crc_verified=matches and actual_crc == expected_crc,
                crc=dict(algorithm="CRC-32/ISO-HDLC", polynomial="0x04C11DB7",
                         init="0xFFFFFFFF", refin=True, refout=True, xorout="0xFFFFFFFF",
                         feed="bytes in ascending Flash address order", field_policy="none; all bytes included",
                         computed_by="host Python over SWD readback; not MCU CRC peripheral",
                         expected=f"0x{expected_crc:08X}", observed=f"0x{actual_crc:08X}"))
