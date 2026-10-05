"""Compare migrated blocks to saved pre-migration statements, including failures."""
import ast
import json
from pathlib import Path
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Stop(Exception):
    pass


class Trace:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def call(self, *event):
        self.calls.append(event)
        if len(self.calls) == self.fail_at:
            raise Stop()

    def evaluate(self, expression, **options):
        self.call('evaluate', expression)
        return len(self.calls)

    def read(self, path, **options):
        self.call('read', path)
        return len(self.calls)

    def check(self, *args):
        self.call('check', *args)


class Literals(dict):
    """Simple NAME = <literal> assignments of a module, for the executed blocks."""

    def __init__(self, source):
        super().__init__()
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                try:
                    self[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    continue


class ScenarioTablesTests(unittest.TestCase):
    def test_every_block_preserves_order_and_first_failure(self):
        fixtures = json.loads(Path(__file__).with_name('scenario_tables.json').read_text(encoding='utf-8'))
        for index, block in enumerate(fixtures['blocks']):
            source = (ROOT / block['file']).read_text(encoding='utf-8')
            # Formatting and teaching comments may change; the migrated statement must not.
            actual_nodes = [ast.dump(node) for node in ast.walk(ast.parse(source))]
            for statement in ast.parse(textwrap.dedent(block['replacement'])).body:
                self.assertIn(ast.dump(statement), actual_nodes)
            helper = next(n for n in ast.parse(source).body
                          if isinstance(n, ast.FunctionDef) and n.name == '_check_values')
            # Constants such as the expected interval are module level in the source.
            namespace = dict(Literals(source))
            exec(compile(ast.Module(body=[helper], type_ignores=[]), block['file'], 'exec'), namespace)
            def execute(code, fail_at=None):
                trace = Trace(fail_at)
                try:
                    exec(textwrap.dedent(code), {**namespace, block['receiver']: trace})
                except Stop:
                    return trace.calls, 'ERROR'
                return trace.calls, 'PASS'
            baseline = execute(block['original'])
            for fail_at in (None, *range(1, len(baseline[0]) + 1)):
                with self.subTest(block=index, fail_at=fail_at):
                    self.assertEqual(execute(block['replacement'], fail_at),
                                     execute(block['original'], fail_at))
