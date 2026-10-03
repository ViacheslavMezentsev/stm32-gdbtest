"""Explicit consumer facts, never inferred from a USB probe identifier."""

CONFIG = {
    'STM32F030R8T6': {'quality':3, 'ram_end':0x20002000, 'nvic_banks':1},
    'STM32F103C8T6': {'quality':1, 'ram_end':0x20005000, 'nvic_banks':2},
    'STM32F411CEU6': {'quality':2, 'ram_end':0x20020000, 'nvic_banks':2},
}


def settings(target):
    return CONFIG[target.profile['mcu']]
