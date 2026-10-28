# Файл стимула принадлежит launcher/GDB, а не адресному пространству MCU.
import json
if request.IsInit:
    gpio = GPIO()
elif request.IsRead or request.IsWrite:
    with open('@STIMULUS@') as stream:
        stimulus = json.load(stream)
    if stimulus['generation'] != gpio.generation:
        gpio.stimulus(stimulus['generation'], stimulus['pins'])
    event = gpio.access(bool(request.IsWrite), int(request.Offset), int(request.Length), int(request.Value))
    if request.IsRead:
        request.Value = event['value']
    with open('@LOG@', 'a') as stream:
        stream.write(json.dumps(event) + '\n')
