"""Target observations, independent of GDB and of backend product-name guesses."""


def check_target(profile, read_memory, image_size, policy, report):
    if policy not in ("warn", "strict"):
        raise ValueError("Identity policy must be warn or strict")
    spec = profile["identity"]
    raw = int.from_bytes(read_memory(spec["address"], 4), "little")
    actual = raw & spec["mask"]
    report["device_id"] = actual
    matched = actual == spec["value"]
    report["identity"] = dict(policy=policy, raw=raw, expected=spec["value"],
                              observed=actual, mask=spec["mask"], matches=matched,
                              selected_mcu=profile["mcu"], selected_profile=profile["name"])
    warnings = report.setdefault("warnings", [])
    if not matched:
        warnings.append(f"DEV_ID mismatch: expected 0x{spec['value']:03X}, observed "
                        f"0x{actual:03X}; selected target remains {profile['mcu']}")
        if policy == "strict":
            raise RuntimeError("DEV_ID mismatch rejected by strict identity policy")
    address = profile.get("flash_size_address")
    if address is None:
        raise RuntimeError("Profile lacks flash_size_address; cannot validate Flash capacity")
    kib = int.from_bytes(read_memory(address, 2), "little")
    report["flash_capacity"] = dict(address=address, raw_kib=kib,
        observed_bytes=kib * 1024, profile_bytes=profile["flash_size"], image_bytes=image_size,
        evidence="16-bit factory size register interpreted by selected profile")
    if kib in (0, 0xFFFF):
        raise RuntimeError("Invalid Flash size register")
    if not 0 < image_size <= min(profile["flash_size"], kib * 1024):
        raise RuntimeError("Image exceeds profile or observed Flash capacity")
    if kib * 1024 != profile["flash_size"]:
        warnings.append(f"Flash capacity differs: profile {profile['flash_size']} bytes, "
                        f"observed {kib * 1024} bytes; image fits both")
