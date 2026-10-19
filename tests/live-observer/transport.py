"""Owned OpenOCD/GDB processes; attach halts and detach never resumes."""
import argparse, datetime, json, socket, subprocess, time, sys, os
from pathlib import Path
from prepare import B, ROOT, sha
from sealed import validate

def save(p, v):
    Path(p).write_text(json.dumps(v, indent=2), encoding='utf-8')

def tool(tc, n):
    return str(Path(tc) / 'bin' / ('arm-none-eabi-' + n + ('.exe' if os.name == 'nt' else '')))
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.backends import load_stand, server_spec
from stm32_gdbtest.processes import spawn_options, stop_tree, probe_lock
from stm32_gdbtest.probes import family
from recovery import validate as validate_backup
import tomllib

def server_commands(stand, profile, port, out):
    spec = server_spec(stand, port, profile, out)
    spec['command'] += ['-c', 'foreach t [target names] { $t configure -event gdb-attach {halt}; $t configure -event gdb-detach {}; $t configure -event gdb-end {} }']
    if 'jlink' in stand.get('interface', ''):
        spec['command'] += ['-c', 'foreach t [target names] { $t configure -event gdb-detach {shutdown} }']
    return spec

def bounded(command, log, timeout):
    with Path(log).open('wb') as f:
        proc = subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT, **spawn_options())
        try:
            code = proc.wait(timeout=timeout)
            if code:
                raise RuntimeError('Process failed: ' + str(code) + ' ' + str(log))
        finally:
            stop_tree(proc)

def phase(action, out, backupdir, stand, profile, g, tc, image=None, p4_package=None, p4_events=None):
    out.mkdir(parents=True, exist_ok=False)
    if action in ('recover', 'load'):
        saved, _ = validate_backup(backupdir)
        if saved['geometry'].get('serial') != stand['serial'] or any((saved['geometry'].get(k) != g[k] for k in ('flash_size', 'ram_size', 'sector'))):
            raise ValueError('Backup belongs to another stand/geometry')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    spec = server_commands(stand, profile, port, out)
    cfg = dict(action=action, source=str(B), backup=str(backupdir), port=port, geometry=g, identity=profile['identity'], objcopy=tool(tc, 'objcopy'), image=str(image) if image else None)
    cfg.update(p4_package=str(p4_package), p4_events=str(p4_events))
    save(out / 'config.json', cfg)
    save(out / 'commands.json', spec)
    script = out / 'entry.gdb'
    script.write_text('python\nOBSERVER_CONFIG=' + repr(str(out / 'config.json')) + '\nexec(compile(open(' + repr(str(B / 'gdb_recovery.py')) + ",encoding='utf-8').read(),'gdb_recovery.py','exec'))\nend\n", encoding='utf-8')
    with probe_lock(out, stand['serial'], 'openocd', family=family(stand)):
        with (out / 'server.log').open('wb') as log:
            server = subprocess.Popen(spec['command'], stdout=log, stderr=subprocess.STDOUT, **spawn_options())
            try:
                deadline = time.monotonic() + stand['startup_timeout_s']
                while spec['ready'].encode() not in (out / 'server.log').read_bytes():
                    if server.poll() is not None or time.monotonic() >= deadline:
                        raise TimeoutError('server readiness')
                    time.sleep(0.05)
                bounded([tool(tc, 'gdb-py3'), '-nx', '-nh', '-batch', '-x', str(script)], out / 'gdb.log', 180)
                if 'jlink' in stand.get('interface', ''):
                    if server.wait(timeout=3) != 0:
                        raise RuntimeError('OpenOCD shutdown failed')
            finally:
                stop_tree(server)
