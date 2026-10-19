"""Remove only demonstrably owned FPB state; ambiguity refuses mutation."""
import json
import struct
from pathlib import Path
from fpb_adapter import Adapter, CTRL, REMAP, COMP

def clear_owned(io, config):
    words = lambda a, n: struct.unpack('<' + 'I' * n, io.read(a, n * 4))
    current = words(CTRL, 10)
    if not any((x & 1 for x in current[2:])) and (not current[1] & 0x1fffffe0):
        return 'NOT_NEEDED'
    package = Path(config['p4_package'])
    from sealed import validate
    m = validate(package)
    events = [json.loads(x) for x in Path(config['p4_events']).read_text().splitlines()]
    snap = next((x for x in reversed(events) if x['event'] == 'snapshot'))
    saved = tuple(snap['fpb'])
    table = m['remap_table']
    target = m['function']
    hook = m['fpb_hook']
    if snap['table'] != table or len(saved) != 10 or any((x & 1 for x in saved[2:])):
        raise RuntimeError('unowned FPB snapshot')
    old = bytes.fromhex(snap['table_bytes'])
    expected = bytearray(32)
    struct.pack_into('<I', expected, 20, 0xf000f8df)
    struct.pack_into('<I', expected, 28, hook | 1)
    if len(old) != 32 or io.read(table, 32) not in (old, bytes(expected)):
        raise RuntimeError('ambiguous remap table')
    for i, (actual, prior) in enumerate(zip(current, saved)):
        allowed = {prior}
        if i == 0:
            allowed = {prior & ~3, prior & ~3 | 1}
        elif i == 1:
            allowed.add(prior & ~0x1fffffe0 | table & 0x1fffffe0)
        elif i == 7:
            allowed.add(target | 1)
        elif i == 9:
            allowed.add(target + 4 | 1)
        if actual not in allowed:
            raise RuntimeError('foreign FPB state')
    adapter = Adapter(io, lambda event: None)
    adapter.saved = saved
    adapter.table = table
    adapter.table_saved = old
    adapter.dirty = True
    result = adapter.remove()
    if result != 'VERIFIED':
        raise RuntimeError('FPB recovery failed: ' + str(adapter.cleanup_error))
    return result
