"""Style of the bundled scenarios, as described in docs/ru/TESTING_TECHNIQUES.md ("Стиль штатных сценариев").

Run directly to list every finding: python tests/host/test_scenario_style.py
A consumer project audits its own scenarios by passing them: python <module>/tests/host/test_scenario_style.py hil/tests/board/*.py
"""
import ast
import io
from pathlib import Path
import re
import sys
import tokenize
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ("tests/firmware/common/tests/board/*.py", "tests/firmware/profiles/*/tests/board/*.py",
             "tests/hal-f030/profile/tests/board/*.py", "tests/hal-f030/hal_scenarios/*.py",
             "examples/minimal-consumer/profile/tests/board/*.py")
LIMIT = 120
SKIP = (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT)
OPENING, CLOSING = "([{", ")]}"
LEGACY = re.compile(r"\btarget\.(?!toml)|\b_check_values\b|\bt\.value\(|\.set_value\(|\.force_return\(|"
                    r"\bt\.fields\(|def \w+\(target\b|except ApiError")
SOURCE_LINE = re.compile(r"""["'][\w./-]+\.[chs]:\d+["']""")
LINE_SCENARIO = "test_until_target.py"  # the one scenario that checks a file:line location


def scenario_files(root=ROOT):
    for pattern in SCENARIOS:
        yield from sorted(root.glob(pattern))


def significant(src):
    return [token for token in tokenize.generate_tokens(io.StringIO(src).readline) if token.type not in SKIP]


def trailing_commas(src):
    """A comma before a closing bracket, except the comma of a one-element tuple."""
    found, stack, tokens = [], [], significant(src)
    for index, token in enumerate(tokens):
        if token.type == tokenize.OP and token.string in OPENING:
            stack.append([token.string, 0])
        elif token.type == tokenize.OP and token.string in CLOSING:
            opener, commas = stack.pop()
            previous = tokens[index - 1]
            if previous.string == "," and not (opener == "(" and commas == 1):
                found.append((previous.start[0], "trailing comma"))
        elif token.string == "," and stack:
            stack[-1][1] += 1
    return found


def continuation_indent(src):
    """Continuation lines align with the opening bracket, or are indented by four when it ends the line."""
    found, stack, lines = [], [], src.splitlines()
    tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    for index, token in enumerate(tokens):
        if token.type == tokenize.OP and token.string in OPENING:
            line = lines[token.start[0] - 1]
            hanging = tokens[index + 1].type in (tokenize.NL, tokenize.COMMENT)
            stack.append((token.start[1] + 1, hanging, len(line) - len(line.lstrip())))
        elif token.type == tokenize.OP and token.string in CLOSING:
            stack.pop()
        elif stack and token.type not in SKIP and tokens[index - 1].type == tokenize.NL:
            visual, hanging, base = stack[-1]
            want = base + 4 if hanging else visual
            if token.start[1] != want:
                found.append((token.start[0], f"continuation indent {token.start[1]}, want {want}"))
    return found


def is_table(node):
    """A list of two or more rows written row by row: check and write tables, constant tables."""
    return any(isinstance(sub, (ast.List, ast.Tuple)) and len(sub.elts) >= 2 and sub.lineno != sub.end_lineno
               and all(isinstance(item, (ast.Tuple, ast.List)) for item in sub.elts) for sub in ast.walk(node))


def joined(lines, first, last):
    """The statement on one line: no space after an opening or before a closing bracket."""
    text = lines[first - 1].rstrip()
    for line in lines[first:last]:
        part = line.strip()
        text += part if text.endswith(tuple(OPENING)) or part.startswith(tuple(CLOSING)) else " " + part
    return text


def needless_breaks(tree, lines):
    """A simple statement broken over lines although it fits the limit on one line."""
    found = []
    compound = (ast.FunctionDef, ast.ClassDef, ast.For, ast.While, ast.If, ast.With, ast.Try)
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt) or isinstance(node, compound) or node.end_lineno == node.lineno:
            continue
        span = lines[node.lineno - 1:node.end_lineno]
        if is_table(node) or any("#" in line or '"""' in line for line in span):
            continue
        text = joined(lines, node.lineno, node.end_lineno)
        if len(text) <= LIMIT:
            found.append((node.lineno, f"statement fits one line ({len(text)})"))
    return found


def target_value(node):
    """t.read("expr") or t.evaluate("expr") without options: a value of the target named by an expression."""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("read", "evaluate") and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "t" and len(node.args) == 1 and not node.keywords
            and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str))


def row_check(node):
    """t.check(name, t.read("expr")[, expected]) with an expected value that is not a Python string."""
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return False
    call = node.value
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == "check" and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "t" and len(call.args) in (2, 3) and target_value(call.args[1])):
        return False
    return len(call.args) == 2 or not (isinstance(call.args[2], ast.Constant) and isinstance(call.args[2].value, str))


def table_candidates(tree):
    """Three or more consecutive checks of target values belong in one check(rows) table."""
    found = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            statements = getattr(node, field, None)
            if not isinstance(statements, list):
                continue
            run = []
            for statement in statements + [None]:
                if statement is not None and row_check(statement):
                    run.append(statement)
                    continue
                if len(run) >= 3:
                    found.append((run[0].lineno, f"{len(run)} consecutive target value checks: use check(rows)"))
                run = []
    return found


def first_line(node):
    return min([decorator.lineno for decorator in getattr(node, "decorator_list", [])] + [node.lineno])


def comments_and_blank_lines(tree, lines):
    found = []
    for node in ast.walk(tree):
        # A comment states the purpose of every function, above its decorators.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = first_line(node)
            if start < 2 or not lines[start - 2].strip().startswith("#"):
                found.append((node.lineno, f"no comment before def {node.name}"))
        # Check tables and loops are explained by a comment.
        table = (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                 and getattr(node.value.func, "attr", "") in ("check", "write") and node.value.args
                 and isinstance(node.value.args[0], (ast.List, ast.ListComp)) and len(node.value.args) == 1)
        if (table or isinstance(node, (ast.For, ast.While))) and not lines[node.lineno - 2].strip().startswith("#"):
            found.append((node.lineno, "table or loop without a comment above"))
    # Two blank lines between top-level definitions and after the imports.
    for previous, current in zip(tree.body, tree.body[1:]):
        definition = (ast.FunctionDef, ast.ClassDef)
        after_imports = isinstance(previous, (ast.Import, ast.ImportFrom)) and not isinstance(
            current, (ast.Import, ast.ImportFrom))
        if not (after_imports or isinstance(previous, definition) or isinstance(current, definition)):
            continue
        start = first_line(current)
        while start > 1 and lines[start - 2].strip().startswith("#"):
            start -= 1
        blank = 0
        while start - blank > 1 and not lines[start - blank - 2].strip():
            blank += 1
        if blank != 2:
            found.append((start, f"{blank} blank lines, want 2"))
    return found


def block_comments(lines):
    """A comment opens a block of a function: one blank line above it, unless it opens the enclosing block."""
    found = []
    for number in range(2, len(lines) + 1):
        line, previous = lines[number - 1], lines[number - 2]
        if not line.startswith(" ") or not line.strip().startswith("#"):
            continue
        if previous.strip() and not previous.strip().startswith("#") and not previous.rstrip().endswith(":"):
            found.append((number, "block comment without a blank line above"))
    return found


def module_constants(tree, lines):
    """A module constant is explained by a comment above it or above the group it continues."""
    found = []
    for previous, node in zip([None] + tree.body, tree.body):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        above = lines[node.lineno - 2].strip() if node.lineno > 1 else ""
        grouped = isinstance(previous, (ast.Assign, ast.AnnAssign)) and previous.end_lineno == node.lineno - 1
        if not above.startswith("#") and not grouped:
            found.append((node.lineno, "module constant without a comment"))
    return found


def audit(path):
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    found = []
    doc = ast.get_docstring(tree, clean=False) or ""
    if not (re.search(r"^\s*RU:", doc, re.M) and re.search(r"^\s*EN:", doc, re.M)):
        found.append((1, "module docstring without RU: and EN: lines"))
    found += [(number, f"line of {len(line)} characters") for number, line in enumerate(lines, 1) if len(line) > LIMIT]
    found += trailing_commas(src) + continuation_indent(src) + needless_breaks(tree, lines)
    found += table_candidates(tree) + comments_and_blank_lines(tree, lines)
    found += block_comments(lines) + module_constants(tree, lines)
    for number, line in enumerate(lines, 1):
        if LEGACY.search(line):
            found.append((number, "former API or name: " + line.strip()[:60]))
        if SOURCE_LINE.search(line) and path.name != LINE_SCENARIO:
            found.append((number, "file:line location outside the until scenario"))
    return sorted(set(found))


class ScenarioStyleTests(unittest.TestCase):
    def test_bundled_scenarios_follow_the_style(self):
        files = list(scenario_files())
        self.assertGreater(len(files), 40)
        report = [f"{path.relative_to(ROOT)}:{number}: {text}" for path in files for number, text in audit(path)]
        self.assertEqual(report, [], "\n".join(report))

    def test_the_audit_sees_each_rule(self):
        sample = ('"""\nRU: x\n"""\nimport os\n\ndef f(target):\n    t.check("a", t.read("x"), 1,)\n'
                  '    t.check("b", t.read("y"), 2)\n    t.check("c", t.read("z"), 3)\n    t.check("d",\n'
                  '                 4)\n    t.until("app.c:12")\n')
        path = ROOT / "build" / "style-sample.py"
        path.parent.mkdir(exist_ok=True)
        path.write_text(sample, encoding="utf-8")
        try:
            texts = " | ".join(text for _, text in audit(path))
        finally:
            path.unlink()
        for expected in ("RU: and EN:", "trailing comma", "continuation indent", "fits one line",
                         "use check(rows)", "no comment before def f", "blank lines", "former API",
                         "file:line location"):
            self.assertIn(expected, texts)


if __name__ == "__main__":
    # Files given on the command line (a consumer's scenarios) replace the bundled set.
    chosen = [Path(name).resolve() for name in sys.argv[1:]] or list(scenario_files())
    findings = 0
    for scenario in chosen:
        for line_number, finding in audit(scenario):
            shown = scenario.relative_to(ROOT) if scenario.is_relative_to(ROOT) else scenario
            print(f"{shown}:{line_number}: {finding}")
            findings += 1
    sys.exit(1 if findings else 0)
