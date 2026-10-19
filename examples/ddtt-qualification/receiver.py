# Учебный приёмник; журнал формируется вне прошивки и GDB.
import json
if request.IsInit:
    sequence = 0
elif request.IsWrite:
    sequence += 1
    event = dict(sequence=sequence, offset=int(request.Offset), width=int(request.Length),
                 value=int(request.Value), accepted=sequence != DROP_SEQUENCE)
    with open(TRACE_PATH, 'a') as stream:
        stream.write(json.dumps(event, sort_keys=True) + '\n')
elif request.IsRead:
    request.Value = 0
