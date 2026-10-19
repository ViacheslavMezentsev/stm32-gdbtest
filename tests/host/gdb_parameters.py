"""Parameter storage for host GDB fakes; settings do not execute the inferior."""
def install(gdb):
    values = {'may-call-functions': True, 'direct-call-timeout': None, 'unwind-on-timeout': False}
    original = getattr(gdb, 'execute', lambda *a, **kw: '')
    def execute(command, **options):
        parts = command.split()
        if len(parts) == 3 and parts[0] == 'set' and parts[1] in values:
            value = parts[2]
            values[parts[1]] = {'on': True, 'off': False, 'unlimited': None}.get(value, value)
            if value.isdigit(): values[parts[1]] = int(value)
            return ''
        return original(command, **options)
    gdb.parameter = values.__getitem__
    gdb.execute = execute
