"""Windows C++/GDB/Renode example; independent of the module runner and Target API."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import shutil
import socket
import subprocess
import sys
import time
import uuid
B = Path(__file__).resolve().parent
ROOT = B.parents[1]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.toolchain import find_gdb


class ScenarioFailure(Exception):
    pass


# Own the emulator lifecycle and preserve evidence even when a stage fails.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--negative-control', action='store_true', help='Expect FAIL (exit 1), not PASS')
    parser.add_argument('--host-only', action='store_true', help='Build and check the C++ cache without Renode')
    parser.add_argument('--gdb', help='GDB executable with embedded Python')
    parser.add_argument('--renode', help='Renode executable (default: PATH)')
    parser.add_argument('--host-cxx', help='Host g++ executable (default: PATH)')
    args = parser.parse_args()
    if args.host_only and args.negative_control:
        parser.error('--negative-control requires the GDB scenario')
    if sys.platform != 'win32':
        parser.error('This example runner supports Windows only')
    if not args.host_only and any(c.isspace() for c in str(ROOT)):
        parser.error('Use a checkout path without whitespace for generated Renode scripts')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
    out = ROOT / 'build' / 'renode-cache' / ('route-' + stamp + '-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True)
    snapshot = out / 'inputs'
    snapshot.mkdir()
    report = dict(schema='renode-cache-example-1', environment='host' if args.host_only else 'emulated', negative_control=args.negative_control, status='ERROR', commands=[], cycles=[], stages=[], model_properties={}, warnings=[])

    def save():
        (out / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def run(label, command, timeout=30):
        row = dict(label=label, command=command)
        report['commands'].append(row)
        save()
        start = time.monotonic()
        try:
            p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW, cwd=out)
            stdout, stderr = (p.stdout, p.stderr)
            row['exit_code'] = p.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = (exc.stdout or b'', exc.stderr or b'')
            row['timeout'] = True
            raise
        finally:
            row['elapsed_s'] = time.monotonic() - start
            if 'stdout' in locals():
                (out / (label + '.stdout.bin')).write_bytes(stdout)
                (out / (label + '.stderr.bin')).write_bytes(stderr)
                (out / (label + '.log')).write_text((stdout + stderr).decode('utf-8', errors='replace'), encoding='utf-8')
            save()
        return p
    # Compile the preserved snapshot, not files that may be edited during a run.
    try:
        inputs = ['run.py', 'scenario_cache.py', 'platform.repl', 'flash_model.py', 'buffered_store.hpp', 'cache_suite.hpp', 'cache_host.cpp', 'cache_calls.cpp', 'cache.ld']
        for name in inputs:
            shutil.copy2(B / name, snapshot / name)
        report['input_sha256'] = {name: hashlib.sha256((snapshot / name).read_bytes()).hexdigest() for name in inputs}
        tools = dict(host=args.host_cxx or shutil.which('g++'))
        if not args.host_only:
            tools.update(gdb=find_gdb(args.gdb), renode=args.renode or shutil.which('renode'))
        if not all(tools.values()):
            raise RuntimeError('Required tool missing')
        tools = {key: str(Path(shutil.which(value) or value).resolve()) for key, value in tools.items()}
        if not args.host_only:
            tools['arm'] = str(Path(tools['gdb']).with_name('arm-none-eabi-g++.exe'))
        report['tools'] = {k: dict(path=v, sha256=hashlib.sha256(Path(v).read_bytes()).hexdigest()) for k, v in tools.items()}
        for key, path in tools.items():
            run('version-' + key, [path, '--version']).check_returncode()
        report['stages'].append('inventory')
        run('host-build', [tools['host'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-O0', '-g', str(snapshot / 'cache_host.cpp'), '-o', str(out / 'host.exe')]).check_returncode()
        host = run('host-test', [str(out / 'host.exe')])
        if host.returncode or b'HOST checks=39 failure_line=0' not in host.stdout:
            raise ScenarioFailure('host contract failed')
        report['stages'].append('host')
        if args.host_only:
            report['status'] = 'PASS'
            return 0
        elf = out / 'neutral.elf'
        run('arm-build', [tools['arm'], '-std=c++17', '-fno-exceptions', '-fno-rtti', '-fno-unwind-tables', '-fno-threadsafe-statics', '-mcpu=cortex-m4', '-mthumb', '-O0', '-g3', '-ffreestanding', '-nostdlib', '-Wl,--build-id=none', '-T', str(snapshot / 'cache.ld'), str(snapshot / 'cache_calls.cpp'), '-o', str(elf)]).check_returncode()
        report['elf_sha256'] = hashlib.sha256(elf.read_bytes()).hexdigest()
        platform = out / 'platform.repl'
        model = (snapshot / 'platform.repl').read_text(encoding='utf-8')
        model = model.replace('@FLASH_MODEL@', (snapshot / 'flash_model.py').as_posix())
        platform.write_text(model, encoding='utf-8')
        report['stages'].append('prepare')
        # Each cycle owns a fresh emulator; do not attach to existing endpoints.
        for cycle in range(1 if args.negative_control else 2):
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            resc = out / f'cycle-{cycle}.resc'
            resc.write_text(f'mach create "sandbox"\nmachine LoadPlatformDescription @{platform.as_posix()}\nsysbus LoadELF @{elf.as_posix()}\nsysbus WriteDoubleWord 0x0800F7FC 0x12345678\nmachine StartGdbServer {port}\n')
            logfile = out / f'renode-{cycle}.bin'
            command = [tools['renode'], '--disable-gui', '--console', '--plain', str(resc)]
            row = dict(cycle=cycle, port=port, status='ERROR', command=command)
            report['cycles'].append(row)
            with logfile.open('wb') as log:
                proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW, cwd=out)
                row['pid'] = proc.pid
                try:
                    deadline = time.monotonic() + 15
                    # Do not probe TCP: connecting can affect the emulated CPU.
                    while b'GDB server with all CPUs started' not in logfile.read_bytes():
                        if proc.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError('Renode readiness failed; inspect raw log')
                        time.sleep(0.05)
                    row['ready'] = True
                    script = out / f'cycle-{cycle}.gdb'
                    script.write_text(f"set pagination off\nset confirm off\ntarget remote 127.0.0.1:{port}\ntbreak cache_done\ncontinue\nset $negative_control = {int(args.negative_control)}\npython\nexec(compile(open({str(snapshot / 'scenario_cache.py')!r}, encoding='utf-8').read(), {str(snapshot / 'scenario_cache.py')!r}, 'exec'))\nend\ndisconnect\n", encoding='utf-8')
                    gdb = run(f'gdb-{cycle}', [tools['gdb'], '-nx', '-nh', '-batch', str(elf), '-x', str(script)], 20)
                    text = (gdb.stdout + gdb.stderr).decode('utf-8', errors='replace')
                    row['gdb_exit'] = gdb.returncode
                    report['warnings'].extend((line for line in text.splitlines() if line.startswith('warning:')))
                    if gdb.returncode:
                        row['status'] = 'FAIL' if 'SCENARIO_ASSERTION_FAILURE' in text else 'ERROR'
                        if row['status'] == 'FAIL':
                            raise ScenarioFailure('GDB assertion failed')
                        raise RuntimeError('GDB command failed')
                    for marker in ['CPP_CALLS_PASS', 'INVALID_SIZE_REFUSED', 'PAGE_BOUNDARIES=', 'MODEL_LOCK_BYPASS=', 'MODEL_PROGRAM_STUB=', 'ELF_CHECK_PASS']:
                        if marker not in text:
                            raise RuntimeError('Missing evidence: ' + marker)
                    row['observations'] = {}
                    for line in text.splitlines():
                        for marker in ['CACHE_RESULT', 'CALL_REGISTERS', 'MODEL_LOCK_BYPASS', 'PAGE_BOUNDARIES', 'MODEL_PROGRAM_STUB']:
                            if line.startswith(marker + '='):
                                row['observations'][marker] = json.loads(line.split('=', 1)[1])
                    if b'non existing peripheral' in logfile.read_bytes():
                        raise RuntimeError('Unmapped access')
                    row['status'] = 'PASS'
                    report['model_properties'] = {'lock_protection': 'NOT_SUPPORTED', 'program_completion_validation': 'NOT_SUPPORTED'}
                except BaseException as exc:
                    row['error'] = repr(exc)  # Retain the primary failure if cleanup also fails.
                    raise
                finally:
                    try:
                        if proc.poll() is None:
                            proc.communicate(b'quit\n', timeout=5)
                    except (subprocess.TimeoutExpired, BrokenPipeError):
                        if proc.poll() is None:
                            run(f'cleanup-{cycle}', ['taskkill', '/PID', str(proc.pid), '/T', '/F'], 5).check_returncode()
                            proc.wait(timeout=5)
                            row['forced_cleanup'] = True
                    row['renode_exit'] = proc.poll()
                    # Evidence of release, not a reservation for the next run.
                    with socket.socket() as free:
                        free.bind(('127.0.0.1', port))
                    row['port_released'] = True
                    save()
            if row['renode_exit'] != 0:
                raise RuntimeError('Renode nonzero exit')
        report['stages'].extend(['scenario', 'evidence', 'cleanup'])
        report['status'] = 'PASS'
    except ScenarioFailure as exc:
        report.update(status='FAIL', error=str(exc))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status='ERROR', error=repr(exc))
    finally:
        report['warnings'] = list(dict.fromkeys(report['warnings']))
        save()
        hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
        (out / 'artifact-sha256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
        print(report['status'], out / 'summary.json')
    return {'PASS': 0, 'FAIL': 1, 'ERROR': 2}[report['status']]
if __name__ == '__main__':
    sys.exit(main())
