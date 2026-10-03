"""Conservative AST inventory of adjacent literal register comparisons."""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def value_call(node, receiver):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == receiver
            and node.func.attr == 'value' and len(node.args) == 1 and not node.keywords
            and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str))


def integer_expression(node):
    if isinstance(node, ast.Constant):
        return type(node.value) is int
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.LShift, ast.RShift, ast.Add, ast.Sub)):
        return integer_expression(node.left) and integer_expression(node.right)
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.Invert)) and integer_expression(node.operand)


def row(statement):
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return None
    call = statement.value
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == 'check'
            and isinstance(call.func.value, ast.Name) and len(call.args) == 3 and not call.keywords):
        return None
    receiver = call.func.value.id
    label, actual, expected = call.args
    if not (isinstance(label, ast.Constant) and isinstance(label.value, str) and value_call(actual, receiver)):
        return None
    if value_call(expected, receiver):
        expected = expected.args[0]
    elif not integer_expression(expected):
        return None
    return ast.Tuple(elts=[label, actual.args[0], expected], ctx=ast.Load())


def survey():
    blocks = []
    files = sorted((ROOT/'tests/firmware/profiles').glob('*/tests/board/test*.py'))
    for path in files:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for parent in ast.walk(tree):
            for _, body in ast.iter_fields(parent):
                if not isinstance(body, list):
                    continue
                pending = []
                for statement in body + [None]:
                    if row(statement) is not None:
                        pending.append(statement)
                    else:
                        if len(pending) >= 3:
                            blocks.append(dict(file=path.relative_to(ROOT).as_posix(),
                                               line=pending[0].lineno, checks=len(pending)))
                        pending = []
    return dict(schema=1, hardware=False, files_scanned=len(files),
                blocks=blocks, total_checks=sum(b['checks'] for b in blocks),
                method='adjacent runs of >=3 literal-label check(value(literal), integer-expression/value(literal)); includes related board variants')


if __name__ == '__main__':
    Path(sys.argv[1]).write_text(json.dumps(survey(), indent=2), encoding='utf-8')
