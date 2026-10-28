"""A5.2: модель GPIO и независимая оценка эффекта вместо доверия ACK."""
import copy
import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "tests/modeled-gpio"


def load(name):
    spec = importlib.util.spec_from_file_location("gpio_" + name, EXAMPLE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


model, analysis = load("model"), load("analysis")


class ModeledGPIOTests(unittest.TestCase):
    def test_external_input_and_ignored_write(self):
        gpio = model.GPIO()
        for generation, pins in enumerate([2, 3, 3, 2, 3, 2], 1):
            gpio.stimulus(generation, pins)
            self.assertEqual(gpio.access(False, 0, 4)["value"], pins)
            ignored = gpio.access(True, 0, 4, pins ^ 1)
            self.assertTrue(ignored["ignored"])
            self.assertEqual(gpio.access(False, 0, 4)["value"], pins)
            self.assertEqual(gpio.pins >> 1, 1)

    def test_invalid_stimulus_is_atomic(self):
        gpio = model.GPIO()
        gpio.stimulus(1, 3)
        for generation, pins in [(1, 2), (0, 2), (True, 2), (2, 4), (2, True)]:
            with self.assertRaises(ValueError):
                gpio.stimulus(generation, pins)
            self.assertEqual((gpio.generation, gpio.pins), (1, 3))
        for offset, width in [(1, 4), (4, 4), (0, 1), (0, 2)]:
            with self.assertRaises(ValueError):
                gpio.access(True, offset, width)
            self.assertEqual(gpio.pins, 3)

    @unittest.skipUnless(shutil.which("g++"), "host C++ compiler required")
    def test_shared_firmware_consumer(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "gpio-host.exe"
            subprocess.run(["g++", "-DHOST", "-O0", str(EXAMPLE / "fixture.cpp"), "-o", str(executable)],
                           check=True, capture_output=True, timeout=60)
            subprocess.run([str(executable)], check=True, capture_output=True, timeout=10)

    def valid(self):
        return dict(scope="modeled-gpio-not-electrical", snapshot={"bytes": 16},
                    consumption=[dict(raw=p, active=p & 1, neighbour=1, samples=i+1)
                                 for i, p in enumerate(analysis.LEVELS)],
                    cpu_callbacks=[[dict(direction="R", width=4, offset=0, value=p, before=p, after=p,
                                         generation=i+1, ignored=False)] for i, p in enumerate(analysis.LEVELS)],
                    refusal={"code": "write_denied", "callbacks": 0},
                    reason_refusal={"code": "write_denied", "callbacks": 0},
                    missing_reason={"refused": True, "callbacks": 0},
                    ack={"acknowledged": True, "verified": False}, override_audit=True,
                    override_callbacks=[dict(direction="W", width=4, offset=0, value=3, before=2,
                                             after=2, generation=1, ignored=True)], readback=2,
                    negative_control={"status": "FAIL", "claim": "override forces input high", "expected": 1, "actual": 0},
                    interruption="intentional interruption before resume",
                    restoration={"memory": True, "input": True}, exception_restoration={"memory": True, "input": True})

    def test_expected_fail_is_not_relabelled_pass(self):
        data = self.valid()
        self.assertTrue(all(c["passed"] for c in analysis.assess(data)))
        self.assertEqual(data["negative_control"]["status"], "FAIL")
        data["negative_control"]["status"] = "PASS"
        self.assertFalse(all(c["passed"] for c in analysis.assess(data)))

    def test_missing_evidence_and_false_ack_claim(self):
        valid = self.valid()
        for key in valid:
            data = copy.deepcopy(valid)
            del data[key]
            self.assertFalse(all(c["passed"] for c in analysis.assess(data)), key)
        for key, value in [("readback", 3), ("scope", "hardware"), ("override_callbacks", []),
                           ("interruption", "unexpected failure"), ("ack", {"acknowledged": True, "verified": True})]:
            data = copy.deepcopy(valid)
            data[key] = value
            self.assertFalse(all(c["passed"] for c in analysis.assess(data)), key)

    def test_extra_read_and_neighbour_corruption(self):
        for mode in ("extra-read", "neighbour", "restore"):
            data = self.valid()
            if mode == "extra-read":
                data["cpu_callbacks"][0] *= 2
            elif mode == "neighbour":
                data["consumption"][1]["neighbour"] = 0
            else:
                data["exception_restoration"]["input"] = False
            self.assertFalse(all(c["passed"] for c in analysis.assess(data)), mode)


if __name__ == "__main__":
    unittest.main()
