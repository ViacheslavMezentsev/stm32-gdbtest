"""Pure recognition helpers; execution and GDB access stay in the scenario."""
import re


def self_branch(pc, assembly):
    tokens = assembly.split()
    if not tokens or tokens[0] not in ('b', 'b.n', 'b.w'):
        return False
    address = re.search(r'0[xX][0-9a-fA-F]+', assembly)
    return address is not None and int(address[0], 16) == pc


def caller_is(frame, name, depth=1):
    if type(depth) is not int or depth < 1:
        raise ValueError('Caller depth must be a positive integer')
    for _ in range(depth):
        frame = frame.older() if frame else None
    return frame is not None and frame.name() == name
