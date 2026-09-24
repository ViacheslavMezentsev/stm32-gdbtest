"""Collect literal test metadata without importing target-side test code."""

import ast
from pathlib import Path
import re


def collect(directory):
    tests = []
    identifiers = set()
    for path in sorted(Path(directory).glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "case"):
                    continue
                if len(decorator.args) != 1:
                    raise ValueError(f"{path}: case requires one literal ID")
                identifier = ast.literal_eval(decorator.args[0])
                if not isinstance(identifier, str) or not re.fullmatch(r"HW_[A-Z0-9_]+", identifier):
                    raise ValueError(f"Invalid case ID: {identifier!r}")
                if identifier in identifiers:
                    raise ValueError(f"Duplicate case ID: {identifier}")
                options = {kw.arg: ast.literal_eval(kw.value) for kw in decorator.keywords}
                if set(options) - {"timeout_s", "labels", "contracts"}:
                    raise ValueError(f"Unsupported case metadata: {identifier}")
                timeout = options.get("timeout_s", 20)
                labels = options.get("labels", ())
                contracts = options.get("contracts", ())
                if not isinstance(contracts, (tuple, list)) or any(
                        not isinstance(x, str) or not re.fullmatch(r"[a-z][a-z0-9_]+", x) for x in contracts):
                    raise ValueError(f"Invalid contracts: {identifier}")
                if len(contracts) != len(set(contracts)):
                    raise ValueError(f"Duplicate contracts: {identifier}")
                if type(timeout) is not int or not 1 <= timeout <= 300:
                    raise ValueError(f"Invalid timeout: {identifier}")
                if not isinstance(labels, (tuple, list)) or any(
                        not isinstance(x, str) or not re.fullmatch(r"[a-z0-9_-]+", x) for x in labels):
                    raise ValueError(f"Invalid labels: {identifier}")
                identifiers.add(identifier)
                tests.append(dict(id=identifier, path=str(path.resolve()), function=node.name,
                                  timeout_s=timeout, labels=list(labels), contracts=list(contracts)))
    if not tests:
        raise ValueError("No hardware cases found")
    return tests


def trace(tests, requirements):
    ids = re.findall(r"^## (HW_[A-Z0-9_]+)\b", Path(requirements).read_text(encoding="utf-8"), re.M)
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate requirement IDs")
    actual = {test["id"] for test in tests}
    if actual != set(ids):
        raise ValueError(f"Missing tests: {sorted(set(ids) - actual)}; missing requirements: {sorted(actual - set(ids))}")
