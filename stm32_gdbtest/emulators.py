"""Owned local emulator configuration and startup (ТЗ 6.12–6.13)."""
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess

from stm32_gdbtest.toolchain import expand_path


def load(document, path):
    if not isinstance(document.get('emulator'), dict):
        raise ValueError('emulator must be a table')
    if document['emulator'].get('backend') == 'qemu':
        return load_qemu(document)
    if set(document) != {'schema', 'emulator', 'renode'} or type(document['schema']) is not int or document['schema'] != 1:
        raise ValueError('Emulator stand requires schema=1, [emulator] and [renode] only')
    data = document['emulator']
    if not isinstance(data, dict) or set(data) - {'backend', 'executable', 'startup_timeout_s', 'shutdown_timeout_s'}:
        raise ValueError('Unknown emulator setting')
    if data.get('backend') != 'renode':
        raise ValueError('Only Renode is supported as an emulator backend')
    limits = {}
    for key, default in [('startup_timeout_s', 15), ('shutdown_timeout_s', 5)]:
        value = data.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 60:
            raise ValueError('Invalid ' + key)
        limits[key] = value
    model = document['renode']
    if not isinstance(model, dict) or set(model) != {'platform'} or not isinstance(model['platform'], str):
        raise ValueError('Renode requires platform only')
    platform = (Path(path).resolve().parent / expand_path(model['platform'])).resolve()
    raw = platform.read_bytes()
    text = raw.decode('utf-8-sig')
    # First public subset: one self-contained REPL; no network or implicit files.
    if re.search(r'(?m)^\s*using\b|\bfilename\s*:|https?://', text):
        raise ValueError('Renode platform must be self-contained (no includes, files or downloads)')
    executable = shutil.which(expand_path(data.get('executable', 'renode')))
    if not executable:
        raise FileNotFoundError('Renode executable not found')
    return dict(backend='renode', environment='emulator', executable=executable,
                platform=str(platform), platform_bytes=raw, remote=None, flash='verify-only', **limits)


def path_argument(path):
    value = Path(path).resolve().as_posix()
    if any(c in value for c in '\r\n";\0'):
        raise ValueError('Unsafe Renode path')
    return '@' + value.replace(' ', '\\ ')


def server_spec(stand, port, profile, out):
    if stand['backend'] == 'qemu':
        return qemu_spec(stand, port, profile, out)
    if profile.get('environment') != 'emulator':
        raise ValueError('Renode requires an emulator target schema 3')
    platform = out / 'platform.repl'
    platform.write_bytes(stand['platform_bytes'])
    config = out / 'renode.config'
    config.write_text('[general]\nuse-synchronous-logging = True\n', encoding='utf-8')
    script = out / 'run.resc'
    script.write_text('mach create "target"\nmachine LoadPlatformDescription ' + path_argument(platform)
                      + '\nsysbus LoadELF ' + path_argument(out / 'firmware.elf')
                      + f'\nmachine StartGdbServer {port}\n', encoding='utf-8')
    return dict(command=[stand['executable'], '--disable-gui', '--console', '--plain', '--config',
                         str(config), '--execute', 'include ' + path_argument(script)],
                ready='GDB server with all CPUs started', reset_halt=None, finish=['disconnect'], setup=[])


def provenance(stand):
    if stand['backend'] == 'qemu':
        return dict(machine=stand['machine'], semihosting=stand['semihosting'],
                    lifetime='per-scenario', reset_supported=False, gdb_bind_scope='127.0.0.1')
    return dict(platform_sha256=hashlib.sha256(stand['platform_bytes']).hexdigest(),
                platform_file='platform.repl', lifetime='per-scenario', reset_supported=False,
                gdb_bind_scope='server-default; may listen on all interfaces')


def stop(process, timeout):
    if process is None:
        return
    if os.name == 'nt':
        if process.poll() is None:
            result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                    capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode and process.poll() is None:
                raise RuntimeError('Cannot stop owned emulator process tree')
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=timeout)


def load_qemu(document):
    """Minimal QEMU contract: an allowlisted single-core machine, no arbitrary args."""
    if set(document) != {'schema', 'emulator', 'qemu'} or type(document['schema']) is not int or document['schema'] != 1:
        raise ValueError('QEMU stand requires schema=1, [emulator] and [qemu] only')
    data = document['emulator']
    if set(data) - {'backend', 'executable', 'startup_timeout_s', 'shutdown_timeout_s'}:
        raise ValueError('Unknown emulator setting')
    model = document['qemu']
    if not isinstance(model, dict) or set(model) - {'machine', 'semihosting'}:
        raise ValueError('Unknown QEMU setting')
    if model.get('machine') != 'netduinoplus2':
        raise ValueError('QEMU currently supports netduinoplus2 only')
    semihosting = model.get('semihosting', False)
    if type(semihosting) is not bool:
        raise ValueError('semihosting must be boolean')
    limits = {}
    for key, default in [('startup_timeout_s', 15), ('shutdown_timeout_s', 5)]:
        value = data.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 60:
            raise ValueError('Invalid ' + key)
        limits[key] = value
    executable = shutil.which(expand_path(data.get('executable', 'qemu-system-arm')))
    if not executable:
        raise FileNotFoundError('QEMU executable not found')
    return dict(backend='qemu', environment='emulator', executable=executable,
                machine=model['machine'], semihosting=semihosting, remote=None,
                flash='verify-only', **limits)


def qemu_spec(stand, port, profile, out):
    if profile.get('environment') != 'emulator':
        raise ValueError('QEMU requires an emulator target schema 3')
    command = [stand['executable'], '-M', stand['machine'], '-display', 'none',
               '-monitor', 'none', '-serial', 'file:' + str(out / 'uart.log'), '-no-reboot',
               '-S', '-gdb', f'tcp:127.0.0.1:{port}', '-kernel', str(out / 'firmware.elf')]
    if stand['semihosting']:
        command += ['-semihosting-config', 'enable=on,target=native']
    return dict(command=command, ready=None, reset_halt=None, finish=['disconnect'], setup=[])
