"""Проверка пригодности журнала транспорта, отдельно от исхода сценария."""
import statistics


def transport_summary(records):
    rows = [r["data"] for r in records if r.get("name") == "host_latency"]
    if len(rows) != 1:
        raise ValueError("one host_latency record required")
    row = rows[0]
    samples = row.get("samples_ns")
    if not isinstance(samples, list) or len(samples) != 6:
        raise ValueError("six raw samples required")
    if any(type(v) is not int or v < 0 for v in samples):
        raise ValueError("nonnegative integer nanoseconds required")
    if row.get("warmup_count") != 1 or row.get("scope") != "host_gdb_roundtrip" or row.get("wcet") is not False:
        raise ValueError("measurement scope mismatch")
    used = samples[1:]
    median, maximum = statistics.median(used), max(used)
    if row.get("median_ns") != median or row.get("max_ns") != maximum:
        raise ValueError("statistics disagree with raw samples")
    return {"status": "VALID", "samples": 6, "used": 5, "median_ns": median,
            "max_ns": maximum, "scope": "host_gdb_roundtrip"}
