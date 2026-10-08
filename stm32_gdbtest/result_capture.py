"""Opt-in journal artifacts; independent of the scenario verdict (ТЗ 5.21)."""

import hashlib
import json
import os
from pathlib import Path
import tempfile

from stm32_gdbtest.configuration import MAXIMUMS
from stm32_gdbtest.records import Journal
from stm32_gdbtest.reports import CODES


# Bounds cover JSON expansion of every permitted journal, including large integers.
MAX_BYTES = 16 * 1024 * 1024


def error(exc):
    return dict(type=type(exc).__name__, message=str(exc))


def save(directory, report, target, completion):
    """Capture before Target.close; never change the scenario verdict."""
    if target is None:
        report['capture'] = dict(status='unavailable', completion='unknown')
        return
    temporary = None
    try:
        records = target.records()
        payload = dict(schema=1, run_id=report['run_id'], case_id=report['id'], records=records)
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
        if len(raw) > MAX_BYTES:
            raise ValueError('records artifact exceeds 16 MiB')
        path = Path(directory) / 'records.json'
        if path.exists() or path.is_symlink():
            raise FileExistsError('records.json already exists')
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.records-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Unique run directories belong to the runner; publish only a fully written file.
        os.replace(temporary, path)
        report['capture'] = dict(status='saved', completion=completion, path='records.json',
                                 sha256=hashlib.sha256(raw).hexdigest(), count=len(records))
    except Exception as exc:
        report['capture'] = dict(status='error', completion=completion, error=error(exc))
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def read(directory, report):
    """Validate ownership, bytes and journal schema before accepting an artifact."""
    meta = report['capture']
    if meta.get('path') != 'records.json' or meta.get('completion') not in ('normal', 'interrupted', 'unknown'):
        raise ValueError('invalid capture metadata')
    path = Path(directory) / 'records.json'
    if path.is_symlink() or path.resolve().parent != Path(directory).resolve():
        raise ValueError('capture escapes run directory')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != meta.get('sha256'):
        raise ValueError('capture size or hash mismatch')

    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate capture key')
            result[key] = value
        return result

    data = json.loads(raw, object_pairs_hook=unique)
    if (type(data) is not dict or set(data) != {'schema', 'run_id', 'case_id', 'records'}
            or type(data['schema']) is not int or data['schema'] != 1
            or data['run_id'] != report['run_id'] or data['case_id'] != report['id']):
        raise ValueError('capture schema or identity mismatch')
    records = data['records']
    if type(records) is not list or type(meta.get('count')) is not int or len(records) != meta['count']:
        raise ValueError('capture count mismatch')
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
        read(directory, report)
    except Exception as exc:
        cause = meta.get('error') or error(exc)
        report['artifact_error'] = cause
        if meta.get('status') == 'saved':
            report['capture'] = dict(status='error', completion=meta.get('completion', 'unknown'), error=cause)
        report['command_code'] = 2
