"""Host-safe, inert argument descriptions for Target.call (ТЗ API 4.23.9)."""
from dataclasses import dataclass
import re

from stm32_gdbtest.errors import fail


NAME = r'[A-Za-z_][A-Za-z_0-9]*(?:::[A-Za-z_][A-Za-z_0-9]*)*'


def invalid(message):
    fail('call', 'validation', 'none', 'invalid_argument', message)


@dataclass(frozen=True)
class Pointer:
    path: str | None
    count: int = 1

    def __post_init__(self):
        if self.path is None and type(self.count) is int and self.count == 0:
            return
        if type(self.path) is not str or len(self.path) > 256 or not re.fullmatch('&?' + NAME, self.path):
            invalid('Pointer requires a named array/pointer or &object')
        if type(self.count) is not int or not 1 <= self.count <= 0x100000:
            invalid('Pointer count must be a positive bounded element count')

    @classmethod
    def null(cls):
        return cls(None, count=0)


@dataclass(frozen=True)
class Reference:
    path: str

    def __post_init__(self):
        if type(self.path) is not str or len(self.path) > 256 or not re.fullmatch(NAME, self.path):
            invalid('Reference requires the name of an existing object')


def describe(value):
    if type(value) is Pointer:
        return dict(kind='pointer', path=value.path, count=value.count)
    if type(value) is Reference:
        return dict(kind='reference', path=value.path)
    return value
