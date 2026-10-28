# -*- coding: utf-8 -*-
"""Учебный GPIO: внешний уровень, RO IDR и независимый журнал обращений."""
class GPIO:
    def __init__(self):
        self.pins = 2
        self.generation = 0

    def stimulus(self, generation, pins):
        if type(generation) is not int or generation <= self.generation:
            raise ValueError("stale stimulus")
        if type(pins) is not int or not 0 <= pins <= 3:
            raise ValueError("only two input pins")
        self.generation, self.pins = generation, pins

    def access(self, write, offset, width, value=0):
        if offset != 0 or width != 4:
            raise ValueError("model supports aligned 32-bit IDR only")
        # Запись подтверждается транспортом, но RO-вход не меняется.
        return dict(direction="W" if write else "R", width=width, offset=offset,
                    value=value if write else self.pins, before=self.pins, after=self.pins,
                    generation=self.generation, ignored=bool(write))
