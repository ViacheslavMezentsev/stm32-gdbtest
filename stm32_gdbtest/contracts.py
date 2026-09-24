"""Declarative ELF contracts. No inferior evaluation, calls or writes."""

import hashlib
import json
from pathlib import Path
import re


def select_contracts(path, names, manifest):
    if not names:
        return {"schema": 1, "contracts": {}}
    raw = Path(path).read_bytes()
    registry = json.loads(raw)
    if type(registry.get("schema")) is not int or registry["schema"] != 1:
        raise ValueError("Unsupported contract schema")
    selected = {}
    for name in names:
        spec = registry["contracts"][name]
        if set(spec) - {"functions", "fields", "enums", "source_reviews", "type_context", "macros"} or not (spec.get("functions") or spec.get("macros")):
            raise ValueError("Invalid contract: " + name)
        if spec.get("functions") and spec.get("type_context") not in spec["functions"]:
            raise ValueError("Invalid type context: " + name)
        if not spec.get("functions") and any(key in spec for key in ("fields", "enums", "type_context")):
            raise ValueError("Type checks require function context: " + name)
        if "macros" in spec:
            macros = spec["macros"]
            if (not isinstance(macros, dict) or set(macros) != {"context", "expressions"}
                    or not isinstance(macros["context"], str)
                    or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", macros["context"])
                    or not isinstance(macros["expressions"], list) or not macros["expressions"]
                    or any(not isinstance(e, str) or not re.fullmatch(
                        r"[A-Za-z_][A-Za-z0-9_]*(?:\([A-Za-z0-9_&, *]*\))?", e)
                        for e in macros["expressions"])):
                raise ValueError("Invalid macro contract: " + name)
        for symbol, function in spec.get("functions", {}).items():
            if set(function) != {"returns", "arguments"} or not isinstance(function["arguments"], list):
                raise ValueError("Invalid function contract: " + symbol)
            args = function["arguments"]
            if any(set(arg) != {"name", "type"} for arg in args) or len({arg["name"] for arg in args}) != len(args):
                raise ValueError("Invalid argument declarations: " + symbol)
        for review in spec.get("source_reviews", []):
            if set(review) != {"file", "sha256", "reason"} or not re.fullmatch("[a-f0-9]{64}", review["sha256"]):
                raise ValueError("Invalid source review")
            matches = [item for item in (manifest or {}).get("inputs", []) if item["file"] == review["file"]]
            if len(matches) != 1 or matches[0]["sha256"] != review["sha256"]:
                raise ValueError("Reviewed source mismatch for " + name + ": " + review["file"])
        selected[name] = spec
    return dict(schema=1, registry_sha256=hashlib.sha256(raw).hexdigest(), contracts=selected)


def inspect_contracts(api, selected):
    report = dict(schema=1, status="PASS", checks=[], errors=[],
                  scope="ELF types, macro presence/expansion and reviewed-source hashes; no runtime semantics")

    def check(name, actual, expected):
        passed = actual == expected
        report["checks"].append(dict(name=name, actual=actual, expected=expected, passed=passed))
        if not passed:
            raise ValueError(name)

    def ctype(name, block):
        # Resolve pointer spelling explicitly: lookup_type accepts names, not C expressions.
        if name.endswith(" *"):
            return ctype(name[:-2], block).pointer()
        if name.startswith("const "):
            return ctype(name[6:], block).const()
        return api.lookup_type(name, block).strip_typedefs()

    for name, spec in selected["contracts"].items():
        try:
            context = None
            for symbol, expected in spec.get("functions", {}).items():
                sym = api.lookup_global_symbol(symbol)
                if sym is None or not sym.is_function:
                    raise ValueError("Function absent from ELF: " + symbol)
                block = api.block_for_pc(int(sym.value().address))
                if symbol == spec["type_context"]:
                    context = block
                kind = sym.type.strip_typedefs()
                check(name + ": " + symbol + " return", kind.target().strip_typedefs() == ctype(expected["returns"], block), True)
                fields = kind.fields()
                args = expected["arguments"]
                check(name + ": " + symbol + " arity", len(fields), len(args))
                for index, argument in enumerate(args):
                    typename = argument["type"]
                    check(name + ": " + symbol + " argument " + str(index),
                          fields[index].type.strip_typedefs() == ctype(typename, block), True)
                actual = {s.name: s.type.strip_typedefs() for s in block if s.is_argument}
                check(name + ": " + symbol + " argument names", sorted(actual), sorted(arg["name"] for arg in args))
                for argument in args:
                    arg, typename = argument["name"], argument["type"]
                    check(name + ": " + symbol + "." + arg, actual[arg] == ctype(typename, block), True)
            for typename, expected in spec.get("fields", {}).items():
                fields = {f.name: f.type.strip_typedefs() for f in ctype(typename, context).fields()}
                for field, fieldtype in expected.items():
                    check(name + ": " + typename + "." + field, fields.get(field) == ctype(fieldtype, context), True)
            for typename, expected in spec.get("enums", {}).items():
                fields = {f.name: f.enumval for f in ctype(typename, context).fields()}
                for field, value in expected.items():
                    check(name + ": " + typename + "." + field, fields.get(field), value)
            if "macros" in spec:
                macros = spec["macros"]
                sym = api.lookup_global_symbol(macros["context"])
                if sym is None or not sym.is_function:
                    raise ValueError("Macro context absent from ELF: " + macros["context"])
                address = int(sym.value().address)
                # Separate offline GDB has no frame. Select source context explicitly.
                api.execute(f"list *0x{address:x}", to_string=True)
                for expression in macros["expressions"]:
                    identifier = expression.split("(", 1)[0]
                    definition = api.execute("info macro " + identifier, to_string=True)
                    check(name + ": defined " + identifier,
                          bool(re.search(r"^#define " + re.escape(identifier) + r"(?:\(|\s|$)", definition, re.M)), True)
                    expansion = api.execute("macro expand " + expression, to_string=True).strip()
                    prefix = "expands to: "
                    if not expansion.startswith(prefix) or expansion[len(prefix):] == expression:
                        raise ValueError("Macro did not expand: " + expression)
                    report.setdefault("macros", []).append(dict(contract=name,
                        context=macros["context"], expression=expression,
                        expansion=expansion[len(prefix):]))
        except Exception as exc:
            report["errors"].append(dict(contract=name, error=str(exc)))
    if report["errors"]:
        report["status"] = "ERROR"
    return report
