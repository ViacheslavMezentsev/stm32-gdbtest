"""Consumer JSON/TOML bridge; no runner or snapshot schema changes."""
import json
from pathlib import Path
from tools import ddtt_qualification as q


def write_data(path, snapshot):
    # JSON внутри TOML сохраняет null и точные типы исходного снимка.
    payload = q.canonical(snapshot).decode('utf-8')
    checksum = q.digest(payload.encode('utf-8'))
    text = 'schema = 1\nsnapshot_sha256 = ' + json.dumps(checksum) + '\nsnapshot_json = ' + json.dumps(payload) + '\n'
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(text)
    return q.digest(Path(path).read_bytes())


def verify_records(result_path, snapshot, data_sha256):
    """Missing, foreign or conflicting records cannot authorize admission."""
    result_path = Path(result_path)
    result = json.loads(result_path.read_text(encoding='utf-8'))
    records = json.loads(result_path.with_name('records.json').read_text(encoding='utf-8'))
    if (records.get('schema') != 1 or records.get('run_id') != result['run_id'] or
            records.get('case_id') != result['id'] or result.get('capture', {}).get('status') != 'saved'):
        raise ValueError('Capture identity or status mismatch')
    selected = [row['data'] for row in records['records'] if row.get('name') == 'qualification_input']
    expected = dict(snapshot=snapshot, snapshot_sha256=q.digest(q.canonical(snapshot)), data_sha256=data_sha256)
    if selected != [expected]:
        raise ValueError('Missing, conflicting or mismatched qualification record')
    return q.digest(result_path.with_name('records.json').read_bytes())
