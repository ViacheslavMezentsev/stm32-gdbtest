"""Behavioral research tests, including an independently authored full-state oracle."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tools.research.adaptive_tree.engine import Engine, ModelError, aggregate, load_tree, read_json
from tools.research.adaptive_tree.run import first_difference
from tools.research.adaptive_tree.player import render


FIXTURE = Path(__file__).parent / 'fixtures/bringup'


def test_case(name, status='PASS', effects=None):
    return {'id': name, 'outcome': status, 'effects': effects or {}}


class AdaptiveTreeTests(unittest.TestCase):
    def test_complete_bringup_oracle(self):
        actual = Engine(load_tree(FIXTURE / 'tree'), read_json(FIXTURE / 'facts.json')).run()
        self.assertIsNone(first_difference(read_json(FIXTURE / 'expected.json'), actual))
        self.assertEqual(list(actual[-1]['results']),
                         ['release', 'key1', 'handshake', 'sample', 'recover', 'key2', 'exchange'])
        self.assertEqual(actual[2]['nodes']['keys']['tests']['key2'], 'BLOCKED')
        self.assertEqual(actual[5]['nodes']['keys']['tests']['key2'], 'PENDING')
        self.assertEqual(actual[-1]['results']['key1']['status'], 'FAIL')

    def test_three_valued_aggregation_truth_table(self):
        rows = [([], None, None), ([None], None, None), ([True, None], None, True),
                ([False, None], False, None), ([True, False], False, True),
                ([True, True], True, True), ([False, False], False, False)]
        for values, all_expected, any_expected in rows:
            self.assertIs(aggregate(values, 'all'), all_expected)
            self.assertIs(aggregate(values, 'any'), any_expected)

    def test_own_aggregate_can_fall_and_ancestor_blocks_true_leaf(self):
        tree = {'id': 'root', 'output': {'ok': {'results': 'all'}},
                'tests': [test_case('a'), test_case('b', 'FAIL')],
                'children': [{'id': 'gate', 'activation': {'input': 'ok'},
                              'children': [{'id': 'leaf', 'tests': [test_case('c')]}]}]}
        states = Engine(tree, {}).run()
        self.assertEqual([s['nodes']['root']['output']['ok'] for s in states], [None, None, False])
        self.assertIs(states[-1]['nodes']['leaf']['condition'], True)
        self.assertFalse(states[-1]['nodes']['leaf']['active'])
        self.assertEqual(states[-1]['nodes']['leaf']['reason'], 'ancestor:gate')
        self.assertNotIn('c', states[-1]['results'])

    def test_any_pass_activates_child_despite_other_failure(self):
        tree = {'id': 'root', 'output': {'ok': {'results': 'any'}},
                'tests': [test_case('a', 'FAIL'), test_case('b')],
                'children': [{'id': 'child', 'activation': {'input': 'ok'},
                              'tests': [test_case('c')]}]}
        states = Engine(tree, {}).run()
        self.assertEqual([s['nodes']['root']['output']['ok'] for s in states], [None, None, True, True])
        self.assertEqual(list(states[-1]['results']), ['a', 'b', 'c'])

    def test_unknown_error_is_not_evidence_of_false_and_independent_work_runs(self):
        tree = {'id': 'root', 'output': {'ok': {'results': 'all'}},
                'tests': [test_case('probe', 'ERROR')], 'children': [
                    {'id': 'dependent', 'activation': {'input': 'ok'}, 'tests': [test_case('blocked')]},
                    {'id': 'independent', 'tests': [test_case('runs')]}]}
        final = Engine(tree, {}).run()[-1]
        self.assertIsNone(final['nodes']['root']['output']['ok'])
        self.assertEqual(final['nodes']['dependent']['reason'], 'condition_unknown')
        self.assertEqual(final['results']['probe']['status'], 'ERROR')
        self.assertEqual(final['results']['runs']['status'], 'PASS')

    def test_reset_invalidates_then_diagnostic_reactivates_without_rerun(self):
        tree = {'id': 'root', 'output': {'ok': {'fact': 'ready'}}, 'children': [
            {'id': 'dependent', 'activation': {'input': 'ok'},
             'tests': [test_case('reset', effects={'ready': None}), test_case('after')]},
            {'id': 'diagnostic', 'tests': [test_case('probe', effects={'ready': True})]}]}
        states = Engine(tree, {'ready': True}).run()
        self.assertEqual(list(states[-1]['results']), ['reset', 'probe', 'after'])
        self.assertEqual(states[1]['nodes']['dependent']['reason'], 'condition_unknown')

    def test_terminal_with_blocked_is_not_all_pass(self):
        tree = {'id': 'root', 'activation': False, 'tests': [test_case('never')]}
        states = Engine(tree, {}).run()
        self.assertEqual(len(states), 1)
        self.assertTrue(states[0]['terminal'])
        self.assertEqual(states[0]['nodes']['root']['tests']['never'], 'BLOCKED')
        self.assertEqual(states[0]['results'], {})

    def test_disabled_node_never_recovers_and_blocks_children(self):
        tree = {'id': 'root', 'enabled': False, 'tests': [test_case('a')],
                'children': [{'id': 'child', 'tests': [test_case('b')]}]}
        final = Engine(tree, {}).run()[-1]
        self.assertEqual(final['nodes']['root']['tests']['a'], 'DISABLED')
        self.assertEqual(final['nodes']['child']['reason'], 'ancestor:root')

    def test_snapshots_are_detached_and_recalculation_is_pure(self):
        engine = Engine(load_tree(FIXTURE / 'tree'), read_json(FIXTURE / 'facts.json'))
        initial = engine.snapshot()
        original = deepcopy(initial)
        self.assertEqual(initial, engine.snapshot())
        engine.step()
        self.assertEqual(initial, original)
        initial['facts']['keys'] = False
        self.assertTrue(engine.facts['keys'])
        state = engine.step()
        state['nodes'].clear()
        self.assertTrue(engine.history[-1]['nodes'])

    def test_step_budget_and_invalid_inputs(self):
        with self.assertRaisesRegex(ModelError, 'budget'):
            Engine({'id': 'r', 'tests': [test_case('a')]}, {}).run(max_steps=0)
        bad = [
            {'id': 'r', 'activation': {'fact': 'typo'}},
            {'id': 'r', 'activation': {'results': 'all'}},
            {'id': 'r', 'tests': [test_case('a', 'SKIP')]},
            {'id': 'r', 'tests': [test_case('a'), test_case('a')]},
            {'id': 'r', 'children': [{'id': 'r'}]},
            {'id': 'r', 'tests': [test_case('a', effects={'typo': True})]},
            {'id': 'r', 'activation': {'eval': 'anything'}},
        ]
        for tree in bad:
            with self.subTest(tree=tree), self.assertRaises(ModelError):
                Engine(tree, {})

    def test_invalid_directory_edges_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'node.json'
            path.write_text('{"id":"r","children":["../outside"]}', encoding='utf-8')
            with self.assertRaises(ModelError):
                load_tree(tmp)
            path.write_text('{"id":"a","id":"b"}', encoding='utf-8')
            with self.assertRaises(ModelError):
                load_tree(tmp)

    def test_oracle_rejects_a_scheduler_mutation(self):
        expected = read_json(FIXTURE / 'expected.json')
        corrupted = deepcopy(expected)
        corrupted[2]['nodes']['keys']['active'] = True
        self.assertEqual(first_difference(expected, corrupted),
                         '$[2].nodes.keys.active: expected False, got True')

    def test_oracle_detects_engine_that_ignores_input_conditions(self):
        class Mutant(Engine):
            def _eval(self, expr, inputs, node):
                if isinstance(expr, dict) and 'input' in expr:
                    return True
                return super()._eval(expr, inputs, node)
        actual = Mutant(load_tree(FIXTURE / 'tree'), read_json(FIXTURE / 'facts.json')).run()
        self.assertIsNotNone(first_difference(read_json(FIXTURE / 'expected.json'), actual))
        self.assertEqual(list(actual[-1]['results'])[:3], ['release', 'key1', 'key2'])

    def test_player_embeds_actual_snapshots_without_script_injection(self):
        frames = Engine(load_tree(FIXTURE / 'tree'), read_json(FIXTURE / 'facts.json')).run()
        html = render(frames)
        payload = html.split('<script id="snapshot-data" type="application/json">')[1].split('</script>')[0]
        import json
        self.assertEqual(json.loads(payload), frames)
        hostile = render([{'reason': '</script><script>alert(1)</script>'}])
        self.assertNotIn('</script><script>alert(1)', hostile)


if __name__ == '__main__':
    unittest.main()
