"""Build/offline integration proof; never starts a debug server."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

session = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
module_root = Path(sys.argv[2]).resolve()
root = Path(session["root"]).resolve()
sys.path.insert(0, str(module_root))
sys.path.insert(1, str(root))
from stm32_gdbtest.build_manifest import digest, load_verified
from stm32_gdbtest.collect import collect
from stm32_gdbtest.contracts import select_contracts
from stm32_gdbtest.runner import local_directory

manifest = load_verified(session["build_manifest"], digest(session["elf"]), session["profile"])
assert {unit["source"] for unit in manifest["units"]} == {"src/main.c", "src/startup.c"}
assert not (root / "stm32_config.yml").exists()
assert Path(session["elf"]).name == "consumer-blink.elf"
assert "profile/consumer_FLASH.ld" in {item["file"] for item in manifest["inputs"]}
cases = collect(session["tests"])
for case in cases:
    spec = importlib.util.spec_from_file_location("consumer_test", case["path"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, case["function"]))
try:
    local_directory(root.parent / "escaped-output", root)
except ValueError:
    pass
else:
    raise AssertionError("Consumer output escaped its project root")
output = local_directory(root / "build/offline", root)
request_path = output / "request.json"
result_path = output / "result.json"
selected = select_contracts(Path(session["profile"]).parent / "Tests/contracts.json",
                            cases[0]["contracts"], manifest)
env = os.environ.copy()
env.update(TMP=str(output), TEMP=str(output), PYTHONDONTWRITEBYTECODE="1",
           STM32_GDBTEST_CONTRACT_REQUEST=str(request_path))
env.pop("PYTHONHOME", None)
env.pop("PYTHONPATH", None)
for negative in (False, True):
    if negative:
        selected["contracts"]["consumer_gpio"]["macros"]["expressions"].append("MISSING_CONSUMER_MACRO")
    result_path.unlink(missing_ok=True)
    request_path.write_text(json.dumps(dict(elf=session["elf"], selected=selected,
                                            result=str(result_path))), encoding="utf-8")
    process = subprocess.run([session["gdb"], "-q", "-nx", "-batch", "-iex", "set auto-load off", session["elf"],
                              "-ex", "source " + (module_root / "stm32_gdbtest/contract_preflight.py").as_posix()],
                             cwd=root, env=env, timeout=30, capture_output=True, text=True)
    (output / ("negative.log" if negative else "positive.log")).write_text(
        process.stdout + process.stderr, encoding="utf-8")
    report = json.loads(result_path.read_text(encoding="utf-8"))
    assert not report["connection_attempted"]
    assert process.returncode == (2 if negative else 0), report
    assert (report["status"] == "PASS") != negative, report
    (output / ("negative.json" if negative else "positive.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8")
print("PASS: consumer manifest, test imports, output isolation, positive/negative offline macro contracts")
