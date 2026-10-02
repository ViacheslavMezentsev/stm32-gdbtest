"""Consumer-only command transform for a controlled HLA/native-DAP comparison."""


def native_swd(command):
    command = list(command)
    if command[1:3] != ['-f', 'interface/stlink.cfg']:
        raise ValueError('Unexpected OpenOCD command; refuse an implicit interface change')
    command[2] = 'interface/stlink-dap.cfg'
    return command[:3] + ['-c', 'transport select dapdirect_swd'] + command[3:]
