"""Trusted GDB commands as a sequence, without splitting quoted semicolons."""


def execute_sequence(execute, commands):
    if isinstance(commands, str):
        raise TypeError('Pass a sequence of complete commands, not a delimited string')
    commands = tuple(commands)
    if not commands or any(not isinstance(c, str) or not c.strip() for c in commands):
        raise ValueError('Commands must be nonempty strings')
    return [execute(command, to_string=True) for command in commands]
