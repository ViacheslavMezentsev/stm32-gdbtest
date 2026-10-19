"""Offline HIL inspection: file links, shared validators and AST only (ТЗ 5.27)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
from stm32_gdbtest.configuration import load_session, capture, ConfigError
from stm32_gdbtest.collect import collect, trace
from stm32_gdbtest import backends, svd


def inspect(*, config=None, session=None, profile_dir=None, test_dirs=(), project_root=None,
            stand=None, local_details=False):
    root = Path(project_root or '.').resolve()
    result = dict(schema=1, scope='structure', runtime_checked=False,
                  selection=dict(mode='session' if session else 'config', source='disk', stand='none'),
                  nodes=[], edges=[], scenarios=[], diagnostics=[],
                  svd=dict(source='none', availability='NOT_CONFIGURED', semantics='NOT_CHECKED', registers=None))
    phase, subject = 'input', 'input'

    def display(path):
        # Никаких исходных TOML, серийников, hostname или текста исключений.
        path = Path(os.path.abspath(path))
        if local_details:
            return str(path)
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return '<external>'

    def diag(code, severity='ERROR', node=None, field=None):
        result['diagnostics'].append(dict(code=code, severity=severity, node=node or subject,
                                         field=field, message=code.replace('.', ' ')))

    def file(role, path, *, raw=None, origin='disk', digest=True):
        path = Path(path)
        found = raw is not None or path.is_file()
        item = dict(id=role, role=role, path=display(path) if origin == 'disk' else None,
                    resolved_path=display(path.resolve()) if origin == 'disk' else None,
                    origin=origin, status='FOUND' if found else 'MISSING', sha256=None)
        if found and digest:
            item['sha256'] = hashlib.sha256(raw if raw is not None else path.read_bytes()).hexdigest()
        result['nodes'].append(item)
        if not found:
            diag('file.missing', node=role)
        return path

    def edge(role, path, base, owner='session', **kwargs):
        file(role, path, **kwargs)
        result['edges'].append(dict(source=owner, target=role, field=role, base_kind=base,
                                    resolver='capture' if kwargs.get('origin') == 'capsule' else 'filesystem',
                                    status=result['nodes'][-1]['status']))

    def deferred(role, owner, base):
        result['nodes'].append(dict(id=role, role=role, path=None, resolved_path=None,
                                   origin=base, status='DEFERRED', sha256=None))
        result['edges'].append(dict(source=owner, target=role, field=role,
                                    base_kind=base, resolver=base, status='DEFERRED'))

    try:
        if bool(config) == bool(session) or (session and (profile_dir or test_dirs)):
            diag('input.conflict')
            return finish(result)
        if config and not profile_dir:
            diag('input.profile_required')
            return finish(result)
        runtime = {}
        capsule = False
        if session:
            phase, subject = 'runtime', 'runtime'
            runtime = json.loads(file('runtime', session).read_text(encoding='utf-8'))
            if not isinstance(runtime, dict):
                raise ValueError('runtime must be an object')
            capsule = '_config_capsule' in runtime
            if not capsule and 'session_config' not in runtime:
                diag('runtime.legacy_unsupported')
                return finish(result)
            roots = [Path(runtime['tests']).parent, *[Path(x).parent for x in runtime.get('test_dirs', [])]]
            if any(not Path(runtime[k]).is_absolute() for k in ('session_config', 'profile', 'tests') if runtime.get(k)):
                diag('runtime.cwd_dependent', 'WARN')
            config = runtime.get('session_config')
            if runtime.get('elf'):
                edge('elf', runtime['elf'], 'cwd', 'runtime', digest=False)
        else:
            base = Path(profile_dir)
            tests = base / 'tests'
            if not tests.is_dir() and (base / 'Tests').is_dir():
                tests = base / 'Tests'
            roots = [tests, *map(Path, test_dirs)]
        phase, subject = 'configuration', 'session'
        if capsule:
            snapshot = capture(runtime)
            result['selection']['source'] = 'capsule'
            if 'session' not in snapshot._source_bytes:
                diag('runtime.legacy_unsupported')
                return finish(result)
            for name, raw in sorted(snapshot._source_bytes.items()):
                role = 'session' if name == 'session' else 'svd' if name == 'svd' else name if name.startswith('data.') else 'config.' + name
                edge(role, role, 'captured-bytes', 'runtime', raw=raw, origin='capsule')
        else:
            entry = file('session', config)
            doc = tomllib.loads(entry.read_text(encoding='utf-8'))
            for group in ('config', 'data'):
                links = doc.get(group, {})
                if isinstance(links, dict):
                    for key, ref in sorted(links.items()):
                        if isinstance(ref, str):
                            edge(group + '.' + key, entry.parent / ref, 'session-dir')
            mmio = doc.get('mmio')
            if isinstance(mmio, dict) and isinstance(mmio.get('svd'), str):
                # Наличие не подразумевает допустимость XML/семантики. Читает bounded loader.
                edge('svd', entry.parent / mmio['svd'], 'session-dir', digest=False)
                result['svd']['availability'] = result['nodes'][-1]['status']
                result['svd']['source'] = 'disk'
            snapshot = capture(runtime) if session else load_session(config)
            # Хеш именно проверенного снимка, а не повторного чтения файла.
            for item in result['nodes']:
                key = item['id'].removeprefix('config.')
                if key in snapshot._source_bytes:
                    item['sha256'] = hashlib.sha256(snapshot._source_bytes[key]).hexdigest()
        if snapshot.svd_catalog is not None:
            result['svd'] = dict(source='capsule' if capsule else 'disk', availability='FOUND',
                                 semantics='VALID', registers=len(snapshot.svd_catalog.registers))
        phase, subject = 'scenarios', 'scenarios'
        result['nodes'].append(dict(id='scenarios', role='scenarios', path=None, resolved_path=None, origin='ast', status='FOUND', sha256=None))
        canonical = set()
        for i, folder in enumerate(roots):
            if folder.resolve() in canonical:
                diag('scenarios.duplicate_root')
            canonical.add(folder.resolve())
            if not (folder / 'board').is_dir():
                diag('scenarios.directory_missing')
            edge('requirements.' + str(i), folder / 'requirements.md', 'scenario-root', 'scenarios')
            if (folder / 'contracts.json').exists():
                edge('contracts.' + str(i), folder / 'contracts.json', 'scenario-root', 'scenarios')
                json.loads((folder / 'contracts.json').read_text(encoding='utf-8'))
        cases = collect([r / 'board' for r in roots])
        phase = 'requirements'
        trace(cases, [r / 'requirements.md' for r in roots])
        result['scenarios'] = [dict(id=t['id'], function=t['function'], path=display(t['path']),
                                    labels=t['labels'], contracts=t['contracts'], timeout_s=t['timeout_s']) for t in cases]
        phase, subject = 'backend', 'stand'
        selected = stand or os.environ.get('STM32_GDBTEST_STAND') or runtime.get('stand')
        result['selection']['stand'] = 'cli' if stand else 'env' if os.environ.get('STM32_GDBTEST_STAND') else 'session' if runtime.get('stand') else 'none'
        if selected:
            path = file('stand', selected)
            parsed = backends.load_stand(path)
            result['backend'] = parsed['backend']
            if parsed.get('remote'):
                deferred('remote-tools', 'stand', 'remote-host')
                edge('ssh', parsed['remote']['ssh'], 'PATH', 'stand', digest=False)
                # Ключ только stat в штатном validator, никогда read/hash/output.
            else:
                edge('executable', parsed['executable'], 'PATH-or-cwd', 'stand', digest=False)
                if parsed.get('platform'):
                    edge('platform', parsed['platform'], 'stand-dir', 'stand', raw=parsed['platform_bytes'])
                if parsed.get('programmer_dir'):
                    edge('programmer', Path(parsed['programmer_dir']) / backends.PROGRAMMER, 'absolute', 'stand', digest=False)
            if parsed['backend'] == 'openocd':
                deferred('openocd-configs', 'stand', 'server-search')
            if parsed.get('environment') == 'emulator':
                if snapshot.config['target'].get('environment') != 'emulator':
                    diag('backend.environment_mismatch')
            elif snapshot.config['target'].get('environment') == 'emulator':
                diag('backend.environment_mismatch')
        else:
            diag('stand.not_selected', 'WARN')
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, SyntaxError) as exc:
        if isinstance(exc, svd.SvdError):
            code = 'svd.source' if exc.code == 'svd.source' else 'svd.integrity' if exc.code == 'svd.integrity' else 'svd.invalid'
            result['svd']['semantics'] = 'NOT_CHECKED' if code == 'svd.source' else 'INVALID'
        elif isinstance(exc, ConfigError):
            code = 'config.' + exc.code if exc.code in {'source', 'session', 'reference', 'target', 'image', 'data', 'api_schema', 'api_parameter', 'conflict', 'stale_selection', 'transport'} else 'config.invalid'
        else:
            code = phase + '.invalid'
        diag(code)
    return finish(result)


def finish(result):
    result['summary'] = {k: sum(x['severity'] == k for x in result['diagnostics']) for k in ('ERROR', 'WARN')}
    result['summary']['DEFERRED'] = sum(x.get('status') == 'DEFERRED' for x in result['edges'])
    result['configuration_valid'] = result['summary']['ERROR'] == 0
    return result


def configure_parser(p):
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--config'); choice.add_argument('--session')
    p.add_argument('--profile-dir'); p.add_argument('--test-dir', action='append', default=[])
    p.add_argument('--project-root'); p.add_argument('--stand'); p.add_argument('--local-details', action='store_true')
    p.add_argument('--format', choices=['text', 'json'], default='text'); p.add_argument('--output')
    p.add_argument('--warnings-as-errors', action='store_true')


def main(a):
    r = inspect(config=a.config, session=a.session, profile_dir=a.profile_dir, test_dirs=a.test_dir,
                project_root=a.project_root, stand=a.stand, local_details=a.local_details)
    text = json.dumps(r, ensure_ascii=False, indent=2) if a.format == 'json' else '\n'.join(
        ['scope: structure; runtime NOT_CHECKED', 'selection: ' + str(r['selection']), 'svd: ' + str(r['svd'])]
        + [f"{n['id']}: {n['path']} {n['status']}" for n in r['nodes']]
        + [f"{x['id']} -> {x['path']}:{x['function']}" for x in r['scenarios']]
        + [f"{e['source']} -> {e['target']} ({e['base_kind']}) {e['status']}" for e in r['edges']]
        + [f"{x['severity']}: {x['code']} [{x['node']}]" for x in r['diagnostics']] + [str(r['summary'])])
    if a.output:
        try:
            Path(a.output).write_text(text + '\n', encoding='utf-8')
        except OSError:
            print('ERROR: output.unwritable', file=sys.stderr)
            return 2
    else:
        print(text)
    return 2 if r['summary']['ERROR'] or (a.warnings_as_errors and r['summary']['WARN']) else 0
