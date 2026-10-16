# Teaching peripheral: journal callback width, model each touched 32-bit register.
import json
if request.IsInit or (request.IsWrite and request.Offset == 0x100):
    words = {0: 15, 4: 0, 8: 15, 12: 15, 24: 0}
    fifo = [11, 22, 33]
    ticks = 0
elif request.IsRead or request.IsWrite:
    offset = int(request.Offset)
    length = int(request.Length)
    before = words.get(offset, 0)
    combined = 0
    effects = []
    for index in range(0, length, 4):
        pos = offset + index
        aligned = pos & ~3
        width = min(4, length - index)
        shift = (pos & 3) * 8
        mask = (1 << (8 * width)) - 1
        old = words.get(aligned, 0)
        forbidden = False
        if request.IsRead:
            value = old
            if aligned == 4:
                value = 0xdead
                forbidden = True
            elif aligned == 16:
                value = fifo.pop(0) if fifo else 0
            elif aligned == 20:
                ticks += 1
                value = ticks
            if aligned == 8: words[aligned] = 0
            combined |= ((value >> shift) & mask) << (8 * index)
        else:
            value = (int(request.Value) >> (8 * index)) & mask
            if aligned == 12:
                words[aligned] = old & ~(value << shift)
            else:
                words[aligned] = (old & ~(mask << shift)) | (value << shift)
        effects.append(dict(offset=aligned, value=value, before=old,
                            after=words.get(aligned, 0), forbidden_read=forbidden))
    if request.IsRead: request.Value = combined
    event = dict(direction='R' if request.IsRead else 'W', offset=offset,
                 value=int(request.Value), before=before, after=words.get(offset, 0),
                 forbidden_read=any(e['forbidden_read'] for e in effects), width=length, effects=effects)
    with open('@LOG@', 'a') as stream:
        stream.write(json.dumps(event) + '\n')
