"""Versioned result reader and bounded, disk-backed completed-event storage."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from collections.abc import Sequence
from stm32_gdbtest.report_codec import pack, expand, canonical
from stm32_gdbtest.errors import ApiError, error_summary

COLLECTIONS = ('checks', 'stops', 'mutations', 'evaluations', 'executions', 'resets')
BLOCK_ROWS = 128
PENDING_BYTES = 1024 * 1024
MAX_ROWS = 65536
MAX_DEFERRED = 128
FILE_BYTES = 16 * 1024 * 1024
EXPANDED_BYTES = 64 * 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 2097152


def plain(value, seen=None, depth=0):
    """Never invoke user conversions, properties or GDB lazy-value access."""
    if depth > MAX_DEPTH:
        return False
    kind = type(value)
    if kind in (str, bool, int, type(None)):
        return True
    if kind is float:
        return math.isfinite(value)
    if kind not in (dict, list):
        return False
    seen = set() if seen is None else seen
    if id(value) in seen:
        return False
    seen.add(id(value))
    try:
        if kind is dict:
            return all(type(k) is str and plain(v, seen, depth + 1) for k, v in value.items())
        return all(plain(v, seen, depth + 1) for v in value)
    finally:
        seen.remove(id(value))


def block(rows):
    payload = pack(rows)
    return dict(count=len(rows), sha256=hashlib.sha256(canonical(payload)).hexdigest(), payload=payload)


def block_rows(item):
    if (type(item) is not dict or set(item) != {'count','sha256','payload'}
            or type(item['count']) is not int or not 1 <= item['count'] <= BLOCK_ROWS):
        raise ValueError('invalid report block')
    if hashlib.sha256(canonical(item['payload'])).hexdigest() != item['sha256']:
        raise ValueError('report block hash mismatch')
    rows = expand(item['payload'], maximum=BLOCK_ROWS)
    if len(rows) != item['count']:
        raise ValueError('report block count mismatch')
    return rows


class Collection(Sequence):
    def __len__(self):
        return self.count

    def __iter__(self):
        for item in self.blocks():
            yield from block_rows(item)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return list(self)[index]
        index = index if index >= 0 else self.count + index
        if not 0 <= index < self.count:
            raise IndexError(index)
        for number, row in enumerate(self):
            if number == index:
                return row


class EventBuffer(Collection):
    """At most 128 plain pending rows; opaque rows retain late repr semantics."""
    def __init__(self):
        self.count = self.deferred = self.spool_bytes = self.pending_bytes = 0
        self.pending = []
        self.parts = []
        self.stream = tempfile.TemporaryFile(mode='w+b')

    def _flush(self):
        if not self.pending:
            return
        raw = canonical(block(self.pending))
        if self.spool_bytes + len(raw) > EXPANDED_BYTES:
            raise ValueError('report spool byte limit exceeded')
        offset = self.stream.seek(0, 2)
        self.stream.write(raw)
        self.stream.flush()
        self.parts.append(('block', offset, len(raw), hashlib.sha256(raw).hexdigest()))
        self.spool_bytes += len(raw)
        self.pending.clear()
        self.pending_bytes = 0

    def append(self, row):
        if self.count >= MAX_ROWS:
            raise ValueError('report row limit exceeded')
        if plain(row):
            raw = canonical(row)
            if len(raw) > FILE_BYTES:
                raise ValueError('report row byte limit exceeded')
            # Commit the preceding block before accepting another row.
            if len(self.pending) == BLOCK_ROWS or self.pending_bytes + len(raw) > PENDING_BYTES:
                self._flush()
            self.pending.append(json.loads(raw))
            self.pending_bytes += len(raw)
        else:
            if self.deferred >= MAX_DEFERRED:
                raise ValueError('report deferred-value limit exceeded')
            self._flush()
            self.parts.append(('deferred', row))
            self.deferred += 1
        self.count += 1

    def __iter__(self):
        # Scenario verdict checks must never trigger repr of a deferred value.
        for part in self.parts:
            if part[0] == 'deferred':
                yield part[1]
            else:
                yield from block_rows(self._read(part))
        yield from copy.deepcopy(self.pending)

    def _read(self, part):
        _, offset, size, checksum = part
        self.stream.seek(offset)
        raw = self.stream.read(size)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError('report spool integrity failure')
        return json.loads(raw)

    def blocks(self):
        # Only serialization calls this method; opaque values convert once, at the end.
        for part in self.parts:
            if part[0] == 'deferred':
                yield block([json.loads(json.dumps(part[1], default=repr, allow_nan=False))])
            else:
                yield self._read(part)
        if self.pending:
            yield block(self.pending)

    def close(self):
        self.stream.close()


class StoredCollection(Collection):
    def __init__(self, data):
        self.data, self.count = data, data['count']

    def blocks(self):
        return iter(self.data['blocks'])


def configure(report, api):
    policy = dict(api.get('report', {}))
    if not policy:
        return
    report['report_policy'] = dict(representation=policy.get('representation','full'),
                                 console=policy.get('console','full'))
    if policy.get('representation') == 'compact':
        for name in COLLECTIONS:
            values = report.setdefault(name, [])
            buf = EventBuffer()
            for row in values:
                buf.append(row)
            report[name] = buf


def append(report, name, row):
    """Preserve the primary exception when a completed event fails to persist."""
    try:
        report.setdefault(name, []).append(row)
    except Exception as cause:
        detail = dict(collection=name, error=error_summary(cause))
        report['report_audit_error_count'] = report.get('report_audit_error_count', 0) + 1
        errors = report.setdefault('report_audit_errors', [])
        if len(errors) < 16:
            errors.append(detail)
        primary = cause.__context__
        if primary is not None:
            if isinstance(primary, ApiError):
                primary.details['report_audit_error'] = detail
            return
        raise ApiError('Completed report event could not be saved', operation='report',
                       stage='audit', effect='unknown', code='report_unavailable',
                       collection=name, audit_error=detail['error']) from cause


def summary(report):
    checks = report.get('checks', [])
    total, failed = 0, 0
    for row in checks:
        total += 1
        failed += row.get('passed') is False
    result = dict(id=report.get('id'), status=report.get('status'), result='result.json',
                  checks_total=total, checks_failed=failed)
    for key in ('error','primary_error','audit_error','report_storage_error','report_audit_errors',
                'execution_cleanup','execution_cleanup_error','teardown_error','warnings'):
        if key in report:
            result[key] = report[key]
    return result


def payload(report, compact):
    data = {k:v for k,v in report.items() if k not in COLLECTIONS} if compact else dict(report)
    if compact:
        encoded_bytes = 0
        data['report_schema'] = 2
        collections = data['collections'] = {}
        for name in COLLECTIONS:
            if name not in report:
                continue
            value = report[name]
            if isinstance(value, Collection):
                blocks = []
                for item in value.blocks():
                    encoded_bytes += len(canonical(item))
                    if encoded_bytes > FILE_BYTES:
                        raise ValueError('report encoded blocks exceed file limit')
                    blocks.append(item)
            else:
                blocks = []
                for i in range(0, len(value), BLOCK_ROWS):
                    item = block(value[i:i+BLOCK_ROWS])
                    encoded_bytes += len(canonical(item))
                    if encoded_bytes > FILE_BYTES:
                        raise ValueError("report encoded blocks exceed file limit")
                    blocks.append(item)
            collections[name] = dict(count=len(value), complete=True, blocks=blocks)
    else:
        data.pop('report_schema', None)
        for name in COLLECTIONS:
            if isinstance(data.get(name), Collection):
                data[name] = list(data[name])
    return data


def write(path, report, *, compact=None):
    """Atomic result publication. No silent fallback or loss on serialization failure."""
    path = Path(path)
    if compact is None:
        compact = report.get('report_policy', {}).get('representation') == 'compact'
    data = payload(report, compact)
    if compact:
        decode(data, materialize=False)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.result-', delete=False) as stream:
            temporary = Path(stream.name)
            size = 0
            for text in json.JSONEncoder(default=repr, ensure_ascii=False, allow_nan=not compact,
                                          separators=(',', ':')).iterencode(data):
                raw = text.encode('utf-8'); size += len(raw)
                if size > FILE_BYTES:
                    raise ValueError('report file exceeds 16 MiB')
                stream.write(raw)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def unique(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate result key')
        data[key] = value
    return data


def bounded(value, depth=0, budget=None):
    budget = [0] if budget is None else budget
    budget[0] += 1
    if depth > MAX_DEPTH + 8 or budget[0] > MAX_NODES:
        raise ValueError('report nesting/node limit')
    if type(value) is dict:
        for k,v in value.items():
            bounded(k,depth+1,budget); bounded(v,depth+1,budget)
    elif type(value) is list:
        for v in value: bounded(v,depth+1,budget)
    elif type(value) is float and not math.isfinite(value):
        raise ValueError('non-finite report value')


def decode(data, *, materialize=True):
    if type(data) is not dict:
        raise ValueError('report must be an object')
    schema = data.get('report_schema', 1)
    if type(schema) is not int or schema not in (1,2):
        raise ValueError('unsupported report schema')
    if schema == 1:
        return data
    bounded(data)
    collections = data.get('collections')
    if type(collections) is not dict or set(collections) - set(COLLECTIONS) or set(data) & set(COLLECTIONS):
        raise ValueError('invalid report collections')
    result = {k:v for k,v in data.items() if k not in ('report_schema','collections')}
    expanded = 0
    for name, section in collections.items():
        if (type(section) is not dict or set(section) != {'count','complete','blocks'}
                or type(section['count']) is not int or not 0 <= section['count'] <= MAX_ROWS
                or section['complete'] is not True or type(section['blocks']) is not list):
            raise ValueError('invalid/incomplete report collection')
        collection = StoredCollection(section)
        count = 0
        for row in collection:
            count += 1
            expanded += len(canonical(row))
            if expanded > EXPANDED_BYTES or count > section['count']:
                raise ValueError('report expansion limit')
        if count != section['count']:
            raise ValueError('report logical count mismatch')
        result[name] = list(collection) if materialize else collection
    return result


def read(path, *, materialize=True):
    with Path(path).open('rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if size > FILE_BYTES:
            raise ValueError('report file exceeds 16 MiB')
        raw = stream.read(size + 1)
    if len(raw) != size:
        raise ValueError('report changed while reading')
    return decode(json.loads(raw, object_pairs_hook=unique), materialize=materialize)


def close(report):
    for name in COLLECTIONS:
        if isinstance(report.get(name), EventBuffer):
            report[name].close()


def observe_execution(report, operation, result, primary):
    if report.get('report_policy', {}).get('representation') != 'compact':
        return
    view = report.setdefault('execution_summary', dict(derived=True, count=0, operations={},
                                                     outcomes={}, first=None, last=None, window='unknown'))
    event = dict(result or {}, operation=operation)
    if primary:
        event['error'] = error_summary(primary)
    view['count'] += 1
    view['operations'][operation] = view['operations'].get(operation, 0) + 1
    outcome = event.get('outcome', 'error')
    view['outcomes'][outcome] = view['outcomes'].get(outcome, 0) + 1
    if view['first'] is None:
        view['first'] = copy.deepcopy(event)
    view['last'] = copy.deepcopy(event)
    if 'generation' in event:
        view.setdefault('first_generation', event['generation'])
        view['last_generation'] = event['generation']
    if outcome == 'started':
        view['window'] = 'open'
    elif outcome in ('stopped','exited'):
        view['window'] = 'closed'
    elif outcome == 'error':
        view['window'] = 'unknown'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Validate a result and export full compatible JSON (no GDB).')
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error('choose a new output file')
    write(args.output, read(args.input), compact=False)
