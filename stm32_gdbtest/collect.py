"""Collect literal test metadata without importing target-side test code."""

import ast
from pathlib import Path
import re


def scenario_dirs(session):
    """Scenario directories of a session: the default one, then the extra search directories (ТЗ API 5.7)."""
    return [session["tests"], *session.get("test_dirs", [])]


def _directories(directories):
    if isinstance(directories, (str, Path)):
        return [Path(directories)]
    return [Path(item) for item in directories]


def collect(directories):
    """Scenarios of one directory or of several, in order; an ID may appear only once in all of them."""
    tests = []
    identifiers = set()
    paths = [path for directory in _directories(directories) for path in sorted(directory.glob("test_*.py"))]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                        and decorator.func.id in ("case", "test")):
                    continue
                if len(decorator.args) != 1:
                    raise ValueError(f"{path}: {decorator.func.id} requires one literal ID")
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
    """Requirements of one file or of several (one per scenario directory) must match the scenarios."""
    files = [requirements] if isinstance(requirements, (str, Path)) else list(requirements)
    ids = [identifier for item in files
           for identifier in re.findall(r"^## (HW_[A-Z0-9_]+)\b", Path(item).read_text(encoding="utf-8"), re.M)]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate requirement IDs")
    actual = {test["id"] for test in tests}
    if actual != set(ids):
        raise ValueError(f"Missing tests: {sorted(set(ids) - actual)}; missing requirements: {sorted(actual - set(ids))}")
