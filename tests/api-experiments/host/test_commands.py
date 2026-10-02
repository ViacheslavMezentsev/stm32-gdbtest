from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.commands import execute_sequence


class CommandSequenceTests(unittest.TestCase):
    def test_quoted_semicolon_remains_one_command(self):
        execute = Mock(return_value='left;right\n')
        self.assertEqual(execute_sequence(execute, ['printf "left;right\\n"']), ['left;right\n'])
        execute.assert_called_once_with('printf "left;right\\n"', to_string=True)

    def test_error_stops_sequence(self):
        execute = Mock(side_effect=[None, RuntimeError('command failed')])
        with self.assertRaisesRegex(RuntimeError, 'command failed'):
            execute_sequence(execute, ['first', 'bad', 'later'])
        self.assertEqual(execute.call_args_list, [call('first', to_string=True), call('bad', to_string=True)])

    def test_entire_input_is_validated_before_execution(self):
        for commands, error in [('one;two', TypeError), ([], ValueError), (['one', ''], ValueError)]:
            execute = Mock()
            with self.assertRaises(error):
                execute_sequence(execute, commands)
            execute.assert_not_called()
