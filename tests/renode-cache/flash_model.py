# Deliberately incomplete teaching peripheral for Renode PythonPeripheral.
# New implementation for this example; no consumer firmware or HAL code.
# Register numbers resemble STM32G4, but this is NOT a hardware implementation.
# LOCK may be overwritten through CR. PG reports EOP without validating payload.
# These omissions are exercised as negative controls, not accepted Flash behavior.
# Keep compatible with Renode's embedded Python (no annotations or f-strings).

if request.IsInit:
    words = {0x14: 0x80000000, 0x10: 0}
    first_key = False
elif request.IsRead:
    request.Value = words.get(request.Offset, 0)
elif request.IsWrite:
    offset = request.Offset
    value = int(request.Value) & 0xFFFFFFFF
    if offset == 0x08:
        unlocked = first_key and value == 0xCDEF89AB
        first_key = (not first_key) and value == 0x45670123
        if unlocked:
            words[0x14] &= 0x7FFFFFFF
    elif offset in (0x10, 0x18):
        words[0x10] &= (~value) & 0xFFFFFFFF
    elif offset == 0x14:
        words[offset] = value
        if value & 0x80000000:
            first_key = False
        elif value & 0x10000:
            if value & 2:
                page = ((value >> 3) & 127) + (128 if value & 0x800 else 0)
                start = 0x08000000 + page * 2048
                bus = self.GetMachine().SystemBus
                for index in range(2048):
                    bus.WriteByte(start + index, 255)
            words[0x10] |= 1
            words[offset] &= 0xFFFEFFFF
        elif value & 1:
            words[0x10] |= 1
    else:
        words[offset] = value
