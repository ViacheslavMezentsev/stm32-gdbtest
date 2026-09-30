"""TC-129: standalone imports, source provenance and original case inventory; no MCU."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[1]))
from stm32_gdbtest.collect import collect

EXPECTED = {"HW_BOOT", "HW_CLOCK", "HW_GPIO", "HW_BLINK", "HW_ADC_DMA_INIT",
            "HW_TIM3_INIT", "HW_RTC_INIT", "HW_ADC_DMA_RUNTIME", "HW_TIM3_IRQ",
            "HW_RTC_ALARM", "HW_ADC_START_ERROR", "HW_ADC_DMA_TIMEOUT",
            "HW_ADC_UNITS", "HW_ADC_INVALID", "HW_ADC_VECTORS",
            "HW_SLEEP_SYSTICK", "HW_SLEEP_TIMER"}
actual = collect(ROOT / "profile/tests/board")
assert len(actual) == len(EXPECTED) and {case["id"] for case in actual} == EXPECTED
for path in sorted((ROOT / "profile/tests/board").glob("test_*.py")):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
provenance = json.loads((ROOT / "provenance/source.json").read_text(encoding="utf-8"))
for entry in provenance["files"]:
    path = (ROOT / entry["destination"]).resolve()
    assert path.is_relative_to(ROOT)
    digest = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert digest == entry["migrated_sha256"], entry["destination"]
print("PASS: 17 cases, standalone imports and migration hashes")
