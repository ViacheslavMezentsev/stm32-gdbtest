"""Preconditions for this reserved layout, not a generic peripheral manager."""
def layout(base, size, vector_size):
    if base != 0x20008000 or size != 4096 or vector_size != 512:
        raise ValueError('ELF ownership/layout mismatch')
    return {'code': base, 'counters': base + 1024, 'vectors': base + 2048}

def can_restore(active, pending):
    if active or pending:
        raise RuntimeError('IRQ not quiescent; keep vector and SRAM')

def fpb_supported(ctrl):
    return ctrl >> 28 == 0 and ctrl >> 4 & 15 > 0

def evidence(expected, original, observed, complete=True):
    if not complete:
        return 'UNKNOWN'
    return 'CONFIRMED' if original == observed == expected else 'FAILED'
