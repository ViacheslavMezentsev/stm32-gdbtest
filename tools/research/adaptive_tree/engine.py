"""Deterministic, simulation-only tree scheduler. No GDB or hardware imports."""
from copy import deepcopy
import json
from pathlib import Path


class ModelError(ValueError):
    pass


def aggregate(values, mode):
    """Three-valued aggregation; empty evidence is unknown, even for all."""
    values = list(values)
    if not values:
        return None
    if mode == 'all':
        return False if False in values else (None if None in values else True)
    if mode == 'any':
        return True if True in values else (None if None in values else False)
    raise ModelError('Unknown aggregation: ' + str(mode))


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ModelError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def load_tree(directory):
    """Directories mirror topology; explicit child lists define order."""
    root = Path(directory).resolve()
    seen = set()

    def visit(path):
        path = path.resolve()
        if not path.is_relative_to(root) or path in seen:
            raise ModelError('Escaping or repeated node directory')
        seen.add(path)
        node = read_json(path / 'node.json')
        children = node.get('children', [])
        if not isinstance(children, list) or any(
                not isinstance(c, str) or not c or c in ('.', '..')
                or '/' in c or '\\' in c for c in children):
            raise ModelError('Children must be direct directory names')
        node['children'] = [visit(path / child) for child in children]
        return node

    return visit(root)


class Engine:
    """Pure expressions + scripted outcomes, one scenario per atomic step."""

    def __init__(self, tree, facts):
        self.facts = deepcopy(facts)
        if not isinstance(facts, dict) or any(
                not isinstance(k, str) or not k or v is not None and type(v) is not bool
                for k, v in facts.items()):
            raise ModelError('Facts must map names to boolean or null')
        self.nodes = []
        self.tests = {}
        self.parents = {}
        self.results = {}
        self.history = []
        self.step_number = 0
        self.provenance = {key: {'step': 0, 'source': 'initial'} for key in facts}

        def expression(expr, inputs):
            if expr is None or type(expr) is bool:
                return
            if not isinstance(expr, dict) or len(expr) != 1:
                raise ModelError('Invalid expression')
            op, arg = next(iter(expr.items()))
            if op in ('fact', 'input'):
                namespace = self.facts if op == 'fact' else inputs
                if not isinstance(arg, str) or arg not in namespace:
                    raise ModelError('Unknown ' + op + ': ' + str(arg))
            elif op == 'results':
                if arg not in ('all', 'any'):
                    raise ModelError('Invalid result aggregation')
            elif op in ('all', 'any') and isinstance(arg, list):
                for item in arg:
                    expression(item, inputs)
            else:
                raise ModelError('Unsupported expression: ' + op)

        ids = set()

        def visit(raw, parent, inputs):
            if not isinstance(raw, dict) or set(raw) - {
                    'id', 'enabled', 'activation', 'output', 'tests', 'children'}:
                raise ModelError('Invalid node fields')
            node = deepcopy(raw)
            name = node.get('id')
            if not isinstance(name, str) or not name or name in ids:
                raise ModelError('Missing or duplicate node ID')
            ids.add(name)
            self.parents[name] = parent
            node.setdefault('enabled', True)
            node.setdefault('activation', True)
            node.setdefault('output', {})
            node.setdefault('tests', [])
            node.setdefault('children', [])
            if type(node['enabled']) is not bool or not isinstance(node['output'], dict):
                raise ModelError('Invalid enabled/output')
            if not isinstance(node['tests'], list) or not isinstance(node['children'], list):
                raise ModelError('Tests and children must be ordered lists')
            if any(not isinstance(k, str) or not k for k in node['output']):
                raise ModelError('Output names must be nonempty strings')
            expression(node['activation'], inputs)
            # Self-result activation would deadlock an initially empty node.
            def uses_results(expr):
                return isinstance(expr, dict) and (
                    'results' in expr or any(uses_results(x) for v in expr.values()
                                             if isinstance(v, list) for x in v))
            if uses_results(node['activation']):
                raise ModelError('Activation cannot depend on own results')
            for expr in node['output'].values():
                expression(expr, inputs)
            for test in node['tests']:
                if not isinstance(test, dict) or set(test) - {'id', 'outcome', 'effects', 'reason'}:
                    raise ModelError('Invalid simulated test fields')
                tid = test.get('id')
                if not isinstance(tid, str) or not tid or tid in self.tests:
                    raise ModelError('Missing or duplicate test ID')
                if test.get('outcome') not in ('PASS', 'FAIL', 'ERROR'):
                    raise ModelError('Invalid simulated outcome')
                effects = test.get('effects', {})
                if not isinstance(effects, dict) or any(
                        k not in self.facts or v is not None and type(v) is not bool
                        for k, v in effects.items()):
                    raise ModelError('Invalid fact effects')
                if 'reason' in test and not isinstance(test['reason'], str):
                    raise ModelError('Reason must be text')
                self.tests[tid] = (name, test)
            self.nodes.append(node)
            for child in node['children']:
                visit(child, name, node['output'])

        visit(tree, None, {})

    def _eval(self, expr, inputs, node):
        if expr is None or type(expr) is bool:
            return expr
        op, arg = next(iter(expr.items()))
        if op == 'fact':
            return self.facts[arg]
        if op == 'input':
            return inputs[arg]
        if op == 'results':
            values = []
            for test in node['tests']:
                status = self.results.get(test['id'], {}).get('status')
                values.append(True if status == 'PASS' else False if status == 'FAIL' else None)
            return aggregate(values, arg)
        return aggregate((self._eval(item, inputs, node) for item in arg), op)

    def snapshot(self):
        rows = {}
        eligible = []
        for node in self.nodes:
            name = node['id']
            parent = rows.get(self.parents[name])
            inputs = parent['output'] if parent else {}
            condition = self._eval(node['activation'], inputs, node)
            if not node['enabled']:
                reason = 'disabled'
            elif parent and not parent['active']:
                reason = 'ancestor:' + self.parents[name]
            elif condition is not True:
                reason = 'condition_false' if condition is False else 'condition_unknown'
            else:
                reason = None
            active = reason is None
            states = {}
            for test in node['tests']:
                tid = test['id']
                if tid in self.results:
                    states[tid] = self.results[tid]['status']
                else:
                    states[tid] = 'PENDING' if active else 'DISABLED' if reason == 'disabled' else 'BLOCKED'
                    if active:
                        eligible.append(tid)
            rows[name] = {
                'parent': self.parents[name], 'input': deepcopy(inputs),
                'output': {key: self._eval(expr, inputs, node)
                           for key, expr in node['output'].items()},
                'condition': condition, 'active': active, 'reason': reason,
                'complete': all(test['id'] in self.results for test in node['tests']),
                'tests': states,
            }
        return deepcopy({'schema': 1, 'step': self.step_number, 'facts': self.facts,
                         'provenance': self.provenance, 'results': self.results,
                         'nodes': rows, 'eligible': eligible,
                         'next': eligible[0] if eligible else None,
                         'terminal': not eligible})

    def step(self):
        before = self.snapshot()
        tid = before['next']
        if tid is None:
            return None
        owner, test = self.tests[tid]
        self.step_number += 1
        self.results[tid] = {'status': test['outcome'], 'step': self.step_number,
                             'node': owner, 'reason': test.get('reason', '')}
        for key, value in test.get('effects', {}).items():
            self.facts[key] = value
            self.provenance[key] = {'step': self.step_number, 'source': tid}
        after = self.snapshot()
        self.history.append(deepcopy(after))
        return after

    def run(self, max_steps=1000):
        if type(max_steps) is not int or max_steps < 0:
            raise ModelError('Invalid step budget')
        snapshots = [self.snapshot()]
        while snapshots[-1]['next'] is not None:
            if len(snapshots) - 1 >= max_steps:
                raise ModelError('Step budget exhausted')
            snapshots.append(self.step())
        return snapshots
