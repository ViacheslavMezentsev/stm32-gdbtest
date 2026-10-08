"""Explicit campaigns and evidence baselines (ТЗ 5.22)."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import uuid

LIMIT = 16 * 1024 * 1024


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result

    with Path(path).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('JSON input exceeds limit')
    try:
        data = json.loads(raw, object_pairs_hook=unique)
        json.dumps(data, allow_nan=False)
    except (RecursionError, OverflowError) as exc:
        raise ValueError('JSON nesting or numeric limit') from exc
    if type(data) is not dict:
        raise ValueError('expected JSON object')
    return data, hashlib.sha256(raw).hexdigest()


def text(value):
    return type(value) is str and bool(value.strip())


def locate(root, relative):
    if not text(relative) or '\\' in relative or ':' in relative:
        raise ValueError('expected portable relative path')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or parts.as_posix() != relative or relative == '.':
        raise ValueError('invalid relative artifact path')
    root = Path(root).resolve()
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('symlink artifact path')
    if not path.resolve().is_relative_to(root):
        raise ValueError('artifact escapes root')
    return path


def file_state(root, path, role, expected=None, budget=None):
    if expected is not None and (type(expected) is not str or re.fullmatch('[0-9a-f]{64}', expected) is None):
        raise ValueError('invalid SHA256')
    source = locate(root, path)
    item = dict(path=path, role=role, expected_sha256=expected)
    if not source.exists():
        return dict(item, state='missing')
    if not source.is_file():
        raise ValueError('artifact is not a regular file')
    digest = hashlib.sha256()
    size = 0
    with source.open('rb') as stream:
        while block := stream.read(1024 * 1024 if budget is None else min(1024 * 1024, budget.remaining + 1)):
            if budget is not None:
                budget.consume(len(block))
            size += len(block)
            digest.update(block)
    actual = digest.hexdigest()
    return dict(item, sha256=actual, size=size,
                state='unverified' if expected is None else 'ok' if actual == expected else 'changed')


def validate_selection(root, selection):
    if (type(selection) is not dict or set(selection) - {'schema', 'campaign_id', 'name', 'runs', 'packages'}
            or type(selection.get('schema')) is not int or selection['schema'] != 1
            or not text(selection.get('name')) or type(selection.get('runs')) is not list
            or type(selection.get('packages', [])) is not list):
        raise ValueError('invalid campaign selection')
    campaign_id = selection.get('campaign_id', str(uuid.uuid4()))
    if not text(campaign_id):
        raise ValueError('invalid campaign_id')
    for spec in selection['runs']:
        if (type(spec) is not dict or not {'result', 'stand'} <= set(spec)
                or set(spec) - {'result', 'stand', 'assigned_id', 'artifacts'}
                or not text(spec['stand']) or type(spec.get('artifacts', {})) is not dict
                or ('assigned_id' in spec and not text(spec['assigned_id']))):
            raise ValueError('invalid run selection')
        locate(root, spec['result'])
        for role, relative in spec.get('artifacts', {}).items():
            if not text(role) or role in ('result', 'records'):
                raise ValueError('invalid or reserved artifact role')
            locate(root, relative)
    for package in selection.get('packages', []):
        if (type(package) is not dict or set(package) != {'path', 'sha256'}
                or type(package['sha256']) is not str or re.fullmatch('[0-9a-f]{64}', package['sha256']) is None):
            raise ValueError('invalid package selection')
        locate(root, package['path'])
    return campaign_id


def build(root, selection):
    campaign_id = validate_selection(root, selection)
    packages, package_paths = [], set()
    for package in selection.get('packages', []):
        if type(package) is not dict or set(package) != {'path', 'sha256'}:
            raise ValueError('invalid package selection')
        if package['path'] in package_paths:
            raise ValueError('duplicate package path')
        package_paths.add(package['path'])
        packages.append(file_state(root, package['path'], 'package', package['sha256']))
    entries, seen = [], set()
    for number, spec in enumerate(selection['runs']):
        if (type(spec) is not dict or set(spec) - {'result', 'stand', 'assigned_id', 'artifacts'}
                or not text(spec.get('stand')) or type(spec.get('artifacts', {})) is not dict
                or ('assigned_id' in spec and not text(spec['assigned_id']))):
            raise ValueError('invalid run selection')
        path = locate(root, spec.get('result'))
        entry = dict(selection_index=number, stand=spec['stand'], diagnostics=[], artifacts=[], package=None)
        report = {}
        try:
            result = file_state(root, spec['result'], 'result')
            entry['artifacts'].append(result)
            if result['state'] == 'missing':
                raise ValueError('missing result')
            report, digest = load(path)
            if digest != result['sha256']:
                raise ValueError('result changed while indexing')
        except (ValueError, OSError, RecursionError) as exc:
            report = {}
            entry['diagnostics'].append(str(exc))
        run_id = report.get('run_id')
        assigned = run_id is None
        if assigned:
            run_id = spec.get('assigned_id')
        if run_id is not None and not text(run_id):
            entry['diagnostics'].append('invalid run_id')
            run_id = None
        if run_id is None:
            entry['diagnostics'].append('no run_id; explicit assigned_id required for legacy data')
        else:
            if run_id in seen:
                raise ValueError('duplicate run_id: ' + run_id)
            seen.add(run_id)
        if not assigned and spec.get('assigned_id') not in (None, run_id):
            raise ValueError('assigned_id conflicts with report')
        entry.update(run_id=run_id, identity_source=None if run_id is None else 'assigned' if assigned else 'report')
        for source, target in [('id', 'case_id'), ('status', 'verdict'), ('mode', 'mode'), ('skip_reason', 'skip_reason')]:
            value = report.get(source)
            entry[target] = value if type(value) is str else None
            if value is not None and type(value) is not str:
                entry['diagnostics'].append('invalid ' + source)
        code = report.get('command_code')
        entry['command_code'] = code if type(code) is int and code in (0, 1, 2) else None
        if code is not None and entry['command_code'] is None:
            entry['diagnostics'].append('invalid command_code')
        if entry['verdict'] not in ('PASS', 'FAIL', 'ERROR', 'SKIP'):
            entry['diagnostics'].append('unknown verdict')
        if entry['verdict'] == 'SKIP' and not text(entry['skip_reason']):
            entry['diagnostics'].append('SKIP without reason')
        capture = report.get('capture')
        entry['capture'] = capture if type(capture) is dict else None
        if capture is not None and type(capture) is not dict:
            entry['diagnostics'].append('invalid capture')
        selected = dict(spec.get('artifacts', {}))
        if 'result' in selected or 'records' in selected:
            raise ValueError('result/records roles are reserved')
        if type(capture) is dict and capture.get('status') == 'saved':
            if capture.get('path') != 'records.json' or not text(capture.get('sha256')):
                entry['diagnostics'].append('invalid saved capture metadata')
            else:
                selected['records'] = (PurePosixPath(spec['result']).parent / 'records.json').as_posix()
        for role, relative in selected.items():
            if not text(role):
                raise ValueError('invalid artifact role')
            expected = capture.get('sha256') if role == 'records' else report.get('elf_sha256') if role == 'elf' else None
            try:
                entry['artifacts'].append(file_state(root, relative, role, expected))
            except (ValueError, OSError) as exc:
                entry['diagnostics'].append(role + ': ' + str(exc))
        package = report.get('package')
        if package is not None:
            if type(package) is not dict or type(package.get('sha256')) is not str or re.fullmatch('[0-9a-f]{64}', package['sha256']) is None:
                entry['diagnostics'].append('invalid package metadata')
            else:
                matches = [p for p in packages if p['expected_sha256'] == package['sha256']]
                entry['package'] = dict(relation='executed_from', evidence='report', sha256=package['sha256'],
                                        artifacts=matches, state='unverified' if not matches else
                                        'missing' if any(p['state'] == 'missing' for p in matches) else
                                        'ok' if all(p['state'] == 'ok' for p in matches) else 'changed')
        entries.append(entry)
    bad = any(e['diagnostics'] or any(a['state'] in ('missing', 'changed') for a in e['artifacts']) for e in entries)
    bad = bad or any(p['state'] in ('missing', 'changed') for p in packages)
    return dict(schema=1, campaign_id=campaign_id, name=selection['name'], runs=entries,
                packages=packages, command_code=2 if bad else 0)


def verify(root, index, budget=None):
    if type(index.get('schema')) is not int or index['schema'] != 1:
        raise ValueError('unsupported index schema')
    checks = []
    for item in index['packages'] + [a for entry in index['runs'] for a in entry['artifacts']]:
        check = file_state(root, item['path'], item['role'], item.get('expected_sha256') or item.get('sha256'), budget)
        if check['state'] == 'ok' and item.get('size') is not None and check['size'] != item['size']:
            check['state'] = 'changed'
        checks.append(check)
    return dict(schema=1, campaign_id=index['campaign_id'], artifacts=checks,
                command_code=2 if any(a['state'] in ('missing', 'changed') for a in checks) else 0)
