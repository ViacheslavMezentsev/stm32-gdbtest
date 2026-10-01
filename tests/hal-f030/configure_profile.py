"""Generate fixture contracts for explicitly reviewed RCC sources; never guess by OS."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

REVIEWED = {
    "fe601fa20f95e48d4bb2a9dd7409ff4d0637e184d6b3c4be4207777b246b2856": False,
    "7ddf83d26b8b9b268df2d1b3c000835360b555aa09727a4c5471e67220d43187": True,
}


def select_registry(registry, source_hash):
    if source_hash not in REVIEWED:
        raise ValueError("Unreviewed F030 RCC source; review NULL guards and signatures before adding hash: " + source_hash)
    result = json.loads(json.dumps(registry))
    for name in ("rcc_error", "rcc_osc_null", "rcc_clock_null"):
        spec = result["contracts"][name]
        for symbol, function in spec["functions"].items():
            if symbol.startswith("HAL_RCC_"):
                arg = function["arguments"][0]
                arg["type"] = ("const " if REVIEWED[source_hash] else "") + arg["type"].removeprefix("const ")
        for review in spec.get("source_reviews", []):
            review["sha256"] = source_hash
            review["reason"] = "Reviewed both RCC NULL guards before assert/dereference; exact type variant selected by reviewed source hash, not OS."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rcc", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "profile"
    registry = json.loads((source / "tests/contracts.json").read_text(encoding="utf-8"))
    selected = select_registry(registry, hashlib.sha256(args.rcc.read_bytes()).hexdigest())
    shutil.copytree(source, args.output, dirs_exist_ok=True)
    (args.output / "tests/contracts.json").write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
