"""Opt-in journal artifacts; independent of the scenario verdict (ТЗ 5.21)."""

import hashlib
import json
import os
from pathlib import Path
import tempfile

from stm32_gdbtest.configuration import MAXIMUMS_V2 as MAXIMUMS
from stm32_gdbtest.compact_records import CompactJournal, decode
from stm32_gdbtest.records import Journal
from stm32_gdbtest.reports import CODES


# Independent artifact bound; a valid in-memory journal can still exceed its JSON byte budget.
MAX_BYTES = 64 * 1024 * 1024


def error(exc):
    return dict(type=type(exc).__name__, message=str(exc))


def save(directory, report, target, completion):
    """Capture before Target.close; never change the scenario verdict."""
    if target is None:
        report['capture'] = dict(status='unavailable', completion='unknown')
        return
    temporary = None
    try:
        journal = getattr(target, '_journal', None)
        if isinstance(journal, CompactJournal):
            payload = journal.payload(report['run_id'], report['id'])
        else:
            records = journal._entries if isinstance(journal, Journal) else target.records()
            payload = dict(schema=1, run_id=report['run_id'], case_id=report['id'], records=records)
        digest, size = hashlib.sha256(), 0
        path = Path(directory) / 'records.json'
        if path.exists() or path.is_symlink():
            raise FileExistsError('records.json already exists')
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.records-', delete=False) as stream:
            temporary = Path(stream.name)
            for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                                          separators=(',', ':')).iterencode(payload):
                raw = chunk.encode('utf-8')
                size += len(raw)
                if size > MAX_BYTES:
                    raise ValueError('records artifact exceeds 64 MiB')
                stream.write(raw)
                digest.update(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Unique run directories belong to the runner; publish only a fully written file.
        os.replace(temporary, path)
        report['capture'] = dict(status='saved', completion=completion, path='records.json',
                                 sha256=digest.hexdigest(), count=len(payload['records']))
    except Exception as exc:
        report['capture'] = dict(status='error', completion=completion, error=error(exc))
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def read(directory, report, *, materialize=True):
    """Validate ownership, bytes and journal schema before accepting an artifact."""
    meta = report['capture']
    if meta.get('path') != 'records.json' or meta.get('completion') not in ('normal', 'interrupted', 'unknown'):
        raise ValueError('invalid capture metadata')
    path = Path(directory) / 'records.json'
    if path.is_symlink() or path.resolve().parent != Path(directory).resolve():
        raise ValueError('capture escapes run directory')
    with path.open('rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if size > MAX_BYTES:
            raise ValueError('capture size exceeds limit')
        raw = stream.read(size + 1)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != meta.get('sha256'):
        raise ValueError('capture size or hash mismatch')

    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate capture key')
            result[key] = value
        return result

    data = json.loads(raw, object_pairs_hook=unique)
    if (type(data) is not dict or type(data.get('schema')) is not int or data['schema'] not in (1, 2)
            or data.get('run_id') != report['run_id'] or data.get('case_id') != report['id']):
        raise ValueError('capture schema or identity mismatch')
    records = data.get('records')
    if type(records) is not list or type(meta.get('count')) is not int or len(records) != meta['count']:
        raise ValueError('capture count mismatch')
    if data['schema'] == 2:
        journal = decode(data)
        return dict(schema=1, source_schema=2, run_id=data['run_id'], case_id=data['case_id'],
                    records=journal.records() if materialize else journal.iter_records())
    if set(data) != {'schema', 'run_id', 'case_id', 'records'}:
        raise ValueError('capture schema fields')
    journal = Journal(**MAXIMUMS)
    for sequence, record in enumerate(records, 1):
        if (type(record) is not dict or set(record) != {'sequence', 'name', 'data'}
                or type(record['sequence']) is not int or record['sequence'] != sequence):
            raise ValueError('invalid record sequence or fields')
        journal.record(record['name'], record['data'])
    return data


def finalize(directory, report, enabled):
    """Add command outcome without hiding a scenario failure or infrastructure error."""
    report['command_code'] = CODES[report['status']]
    if not enabled or report.get('mode') == 'prepare':
        return
    meta = report.setdefault('capture', dict(status='unavailable', completion='unknown'))
    try:
        if meta.get('status') != 'saved':
            raise ValueError('required capture unavailable')
        read(directory, report, materialize=False)
    except Exception as exc:
        cause = meta.get('error') or error(exc)
        report['artifact_error'] = cause
        if meta.get('status') == 'saved':
            report['capture'] = dict(status='error', completion=meta.get('completion', 'unknown'), error=cause)
        report['command_code'] = 2
