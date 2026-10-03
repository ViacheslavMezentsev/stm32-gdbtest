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

    def value(self, expression):
        self.call('value', expression)
        return len(self.calls)

    def check(self, *args):
        self.call('check', *args)


class ScenarioTablesTests(unittest.TestCase):
    def test_every_block_preserves_order_and_first_failure(self):
        fixtures = json.loads(Path(__file__).with_name('scenario_tables.json').read_text(encoding='utf-8'))
        for index, block in enumerate(fixtures['blocks']):
            source = (ROOT / block['file']).read_text(encoding='utf-8')
            self.assertIn(block['replacement'], source)
            helper = next(n for n in ast.parse(source).body
                          if isinstance(n, ast.FunctionDef) and n.name == '_check_values')
            namespace = {}
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
