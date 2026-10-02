"""Finite projected call order; mismatch never consumes an expectation."""


class CallOrder:
    def __init__(self, expected):
        self.expected = tuple(expected)
        self.position = 0

    def observe(self, actual):
        expected = self.expected[self.position] if self.position < len(self.expected) else '<end>'
        if self.position == len(self.expected) or actual != expected:
            raise ValueError(f'Call order at {self.position}: expected {expected}, observed {actual}')
        self.position += 1

    def complete(self):
        if self.position != len(self.expected):
            raise ValueError(f'Incomplete call order: {self.position}/{len(self.expected)}')
