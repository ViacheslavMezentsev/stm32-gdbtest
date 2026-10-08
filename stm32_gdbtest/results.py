"""Offline result tools: bounded snapshots and publication (ТЗ 5.22)."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from stm32_gdbtest import result_index as indexer
from stm32_gdbtest import result_export as exporter
from stm32_gdbtest.result_files import Budget, ownership, publish_json, write_json


@dataclass(frozen=True)
class Limits:
    runs: int = 128
    files: int = 2048
    input_bytes: int = 256 * 1024 * 1024
    output_bytes: int = 64 * 1024 * 1024
    series: int = 32

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in vars(self).values()):
            raise ValueError('limits must be positive integers')


def validate_index(root, index, limits=Limits()):
    """Validate the imported M2b shape before using its paths or baseline hashes."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def nullable_string(value):
        return value is None or type(value) is str

    def digest(value):
        return value is None or (type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None)

    require(type(index) is dict and set(index) == {'schema', 'campaign_id', 'name', 'runs', 'packages', 'command_code'}, 'index fields')
    require(type(index['schema']) is int and index['schema'] == 1, 'index schema')
    require(indexer.text(index['campaign_id']) and indexer.text(index['name']), 'campaign identity')
    require(type(index['command_code']) is int and index['command_code'] in (0, 2), 'index command code')
    require(type(index['runs']) is list and len(index['runs']) <= limits.runs, 'run limit/type')
    require(type(index['packages']) is list, 'packages type')
    artifacts = list(index['packages'])
    seen = set()
    for number, entry in enumerate(index['runs']):
        fields = {'selection_index', 'stand', 'diagnostics', 'artifacts', 'package', 'run_id', 'identity_source',
                  'case_id', 'verdict', 'mode', 'skip_reason', 'command_code', 'capture'}
        require(type(entry) is dict and set(entry) == fields, 'run fields')
        require(type(entry['selection_index']) is int and entry['selection_index'] == number, 'selection index')
        require(indexer.text(entry['stand']), 'stand label')
        require(type(entry['diagnostics']) is list and all(type(d) is str for d in entry['diagnostics']), 'diagnostics')
        require(all(nullable_string(entry[k]) for k in ('run_id', 'case_id', 'verdict', 'mode', 'skip_reason')), 'run text fields')
        require(entry['identity_source'] in (None, 'assigned', 'report'), 'identity source')
        if entry['run_id'] is not None:
            require(indexer.text(entry['run_id']) and entry['run_id'] not in seen, 'duplicate/empty run_id')
            require(entry['identity_source'] is not None, 'missing identity source')
            seen.add(entry['run_id'])
        else:
            require(entry['identity_source'] is None, 'identity without ID')
        require(entry['command_code'] is None or (type(entry['command_code']) is int and entry['command_code'] in (0, 1, 2)), 'run command code')
        require(entry['capture'] is None or type(entry['capture']) is dict, 'capture type')
        # Capture is opaque source metadata here, never interpreted as a measurement schema.
        require(type(entry['artifacts']) is list, 'artifact list')
        artifacts.extend(entry['artifacts'])
        package = entry['package']
        if package is not None:
            require(type(package) is dict and set(package) == {'relation', 'evidence', 'sha256', 'artifacts', 'state'}, 'package fields')
            require(package['relation'] == 'executed_from' and package['evidence'] == 'report', 'package relation')
            require(package['sha256'] is not None and digest(package['sha256']), 'package digest')
            require(package['state'] in ('ok', 'missing', 'changed', 'unverified'), 'package state')
            require(type(package['artifacts']) is list and all(p in index['packages'] for p in package['artifacts']), 'package references')
    require(len(artifacts) <= limits.files, 'artifact count limit')
    for item in artifacts:
        require(type(item) is dict and {'path', 'role', 'expected_sha256', 'state'} <= set(item)
                and not set(item) - {'path', 'role', 'expected_sha256', 'state', 'sha256', 'size'}, 'artifact fields')
        indexer.locate(root, item['path'])
        require(indexer.text(item['role']) and digest(item['expected_sha256']), 'artifact role/digest')
        require(item['state'] in ('ok', 'missing', 'changed', 'unverified'), 'artifact state')
        if item['state'] == 'missing':
            require('sha256' not in item and 'size' not in item, 'missing artifact with observed data')
        else:
            require(item.get('sha256') is not None and digest(item.get('sha256')), 'observed hash')
            require(type(item.get('size')) is int and item['size'] >= 0, 'artifact size')
            expected = item['expected_sha256']
            state = 'unverified' if expected is None else 'ok' if expected == item['sha256'] else 'changed'
            require(item['state'] == state, 'inconsistent artifact state')
    return artifacts


class Snapshot:
    def __init__(self, root, destination, limits):
        self.root, self.destination, self.limits = Path(root), destination, limits
        self.entries, self.total = {}, 0

    def copy(self, relative):
        if relative in self.entries:
            return
        if len(self.entries) >= self.limits.files:
            raise ValueError('input file count limit')
        source = indexer.locate(self.root, relative)
        if not source.exists():
            self.entries[relative] = None
            return
        if not source.is_file():
            raise ValueError('input not a regular file')
        target = self.destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with source.open('rb') as src, target.open('xb') as dst:
            while block := src.read(min(1024 * 1024, self.limits.input_bytes - self.total + 1)):
                self.total += len(block)
                if self.total > self.limits.input_bytes:
                    raise ValueError('aggregate input size limit')
                digest.update(block)
                dst.write(block)
        self.entries[relative] = digest.hexdigest()

    def unchanged(self):
        budget = Budget(self.limits.input_bytes, 'source recheck')
        for relative, expected in self.entries.items():
            state = indexer.file_state(self.root, relative, 'source', expected, budget)
            if (expected is None and state['state'] != 'missing') or (expected is not None and state['state'] != 'ok'):
                raise ValueError('source changed during processing: ' + relative)


def pipeline(root, selection, output, config=None, limits=Limits()):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if type(selection) is not dict or type(selection.get('runs')) is not list or len(selection['runs']) > limits.runs:
        raise ValueError('selection run limit/type')
    indexer.validate_selection(root, selection)
    with ownership(output), tempfile.TemporaryDirectory(prefix='.results-', dir=output.parent) as temporary:
        temporary = Path(temporary)
        sources = temporary / 'inputs'
        sources.mkdir()
        snapshot = Snapshot(root, sources, limits)
        for spec in selection['runs']:
            snapshot.copy(spec['result'])
            for relative in spec.get('artifacts', {}).values():
                snapshot.copy(relative)
            path = sources / spec['result']
            try:
                report, _ = indexer.load(path)
            except (ValueError, OSError, RecursionError):
                continue
            capture = report.get('capture')
            if type(capture) is dict and capture.get('status') == 'saved' and capture.get('path') == 'records.json':
                snapshot.copy((Path(spec['result']).parent / 'records.json').as_posix())
        for package in selection.get('packages', []):
            snapshot.copy(package['path'])
        local_config = None
        if config is not None:
            config = Path(config)
            with config.open('rb') as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ValueError('export configuration size limit')
            local_config = temporary / 'export.toml'
            local_config.write_bytes(raw)
        specs = exporter.definitions(local_config)
        if len(specs) > limits.series:
            raise ValueError('series count limit')
        # Conservative bound before materializing projections; final encoded bytes are checked as well.
        journal_bytes = sum((sources / p).stat().st_size for p, h in snapshot.entries.items()
                            if h is not None and Path(p).name == 'records.json')
        if journal_bytes * (4 + 3 * len(specs)) > limits.output_bytes:
            raise ValueError('estimated output size limit')
        index = indexer.build(sources, selection)
        validate_index(sources, index, limits)
        selected = [e['selection_index'] for e in index['runs'] if e['mode'] != 'prepare']
        reports = [sources / selection['runs'][i]['result'] for i in selected]
        product = temporary / 'product'
        budget = Budget(limits.output_bytes, 'output')
        bundle = exporter.export(reports, product, local_config, budget=budget, selection_indices=selected)
        write_json(product / 'index.json', index, budget)
        if (product / 'index.json').stat().st_size > indexer.LIMIT:
            raise ValueError('index exceeds readable JSON input limit')
        write_json(product / 'selection.json', selection, budget)
        if local_config is not None:
            budget.consume(local_config.stat().st_size)
            shutil.copyfile(local_config, product / 'export.toml')
        write_json(product / 'source-hashes.json', snapshot.entries, budget)
        code = max(index['command_code'], bundle['command_code'])
        write_json(product / 'summary.json', dict(schema=1, campaign_id=index['campaign_id'], command_code=code,
                                             index_code=index['command_code'], export_code=bundle['command_code'],
                                             runs=len(index['runs']), records=len(bundle['records']),
                                             measurements=len(bundle['measurements']), limits=vars(limits)), budget)
        if sum(p.stat().st_size for p in product.iterdir()) > limits.output_bytes:
            raise ValueError('encoded output size limit')
        snapshot.unchanged()
        if output.exists() or output.is_symlink():
            raise FileExistsError(output)
        product.rename(output)
    return code


def check(root, index, limits=Limits()):
    artifacts = validate_index(root, index, limits)
    return indexer.verify(root, index, Budget(limits.input_bytes, 'verification input'))


def verify_to_file(root, index, output, limits=Limits()):
    result = check(root, index, limits)
    publish_json(output, result, Budget(limits.output_bytes, 'output'))
    return result['command_code']


def configure_cli(subs):
    parser = subs.add_parser('results', help='offline journal export and evidence verification')
    commands = parser.add_subparsers(dest='results_command', required=True)
    export_parser = commands.add_parser('export', help='build index and generic/measurement exports')
    export_parser.add_argument('--selection', type=Path, required=True)
    export_parser.add_argument('--config', type=Path, help='optional projection TOML')
    verify_parser = commands.add_parser('verify', help='compare evidence against a saved index')
    verify_parser.add_argument('--index', type=Path, required=True)
    for command in (export_parser, verify_parser):
        command.add_argument('--root', type=Path, required=True, help='explicit evidence root')
        command.add_argument('--output', type=Path, required=True, help='new directory (export) or file (verify)')
        for name, default in vars(Limits()).items():
            command.add_argument('--max-' + name.replace('_', '-'), type=int, default=default)


def main(args):
    limits = Limits(**{name: getattr(args, 'max_' + name) for name in vars(Limits())})
    document, _ = indexer.load(args.selection if args.results_command == 'export' else args.index)
    if args.results_command == 'export':
        code = pipeline(args.root, document, args.output, args.config, limits)
    else:
        code = verify_to_file(args.root, document, args.output, limits)
    print(f"Results {args.results_command}: command_code={code}; {args.output}")
    return code
