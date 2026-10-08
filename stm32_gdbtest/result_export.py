"""Generic journal export and explicit field projections (ТЗ 5.22)."""

import csv
import hashlib
import json
import math
from pathlib import Path
import tomllib

from stm32_gdbtest.result_capture import MAX_BYTES, read
from stm32_gdbtest.errors import RecordError
from stm32_gdbtest.result_files import Budget, output_stream, write_json


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def load_report(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('report exceeds input limit')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result

    report = json.loads(raw, object_pairs_hook=unique)
    encoded(report)
    if type(report) is not dict:
        raise ValueError('report must be an object')
    for key in ('id', 'run_id'):
        if type(report.get(key)) is not str or not report[key]:
            raise ValueError('missing identity: ' + key)
    if type(report.get('capture')) is not dict or report['capture'].get('status') != 'saved':
        raise ValueError('journal not saved')
    return report, hashlib.sha256(raw).hexdigest()


def definitions(path):
    if path is None:
        return []
    with Path(path).open('rb') as stream:
        data = tomllib.load(stream)
    if (set(data) != {'schema', 'series'} or type(data['schema']) is not int
            or data['schema'] != 1 or type(data['series']) is not list):
        raise ValueError('expected schema=1 and series array')
    names = set()
    for row in data['series']:
        required = {'name', 'record', 'path', 'unit'}
        if type(row) is not dict or not required <= set(row) or set(row) - required - {'scale', 'offset'}:
            raise ValueError('invalid series fields')
        if any(type(row[k]) is not str or not row[k] for k in ('name', 'record', 'unit')):
            raise ValueError('series names and unit must be nonempty strings')
        if row['name'] in names:
            raise ValueError('duplicate series name')
        names.add(row['name'])
        if type(row['path']) is not list or any(type(key) is not str for key in row['path']):
            raise ValueError('path must be an array of dictionary keys')
        for key in ('scale', 'offset'):
            if key in row and (type(row[key]) not in (int, float)
                               or (type(row[key]) is float and not math.isfinite(row[key]))):
                raise ValueError('scale/offset must be finite numbers')
    return data['series']


def project(record, spec):
    row = dict(sequence=record['sequence'], record=record['name'], series=spec['name'],
               unit=spec['unit'], state='value')
    value = record['data']
    for key in spec['path']:
        if type(value) is not dict:
            return dict(row, state='error', error='path traverses a non-object')
        if key not in value:
            return dict(row, state='missing')
        value = value[key]
    row['raw_value'] = value
    if value is None:
        return dict(row, state='null', value=None)
    try:
        transformed = value
        if 'scale' in spec or 'offset' in spec:
            if type(value) not in (int, float):
                raise ValueError('arithmetic requires a number, not bool/string/container')
            transformed = value * spec.get('scale', 1) + spec.get('offset', 0)
        encoded(transformed)
        return dict(row, value=transformed)
    except (ValueError, OverflowError) as exc:
        return dict(row, state='error', error=str(exc))


def export(paths, output, config=None, *, budget=None, selection_indices=None):
    """Explicit source list, no scanning, no verdict changes, no partial source projection."""
    specs = definitions(config)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    sources, generic, measurements, diagnostics = [], [], [], []
    identities = set()
    for source_index, path in enumerate(paths):
        path = Path(path)
        try:
            report, digest = load_report(path)
            snapshot = read(path.parent, report)
            if report['run_id'] in identities:
                raise ValueError('duplicate run_id')
            identities.add(report['run_id'])
            origin = dict(run_id=report['run_id'], case_id=report['id'])
            sources.append(dict(source_index=source_index, **origin, result_sha256=digest,
                                records_sha256=report['capture']['sha256'],
                                verdict=report.get('status'), command_code=report.get('command_code')))
            generic.extend(dict(origin, **record) for record in snapshot['records'])
            for spec in specs:
                matches = [record for record in snapshot['records'] if record['name'] == spec['record']]
                if not matches:
                    diagnostics.append(dict(source_index=source_index, series=spec['name'], error='no matching records'))
                for record in matches:
                    row = dict(origin, **project(record, spec))
                    measurements.append(row)
                    if row['state'] in ('missing', 'error'):
                        diagnostics.append(dict(source_index=source_index, series=spec['name'],
                                                sequence=record['sequence'], error=row.get('error', 'missing field')))
        except (ValueError, TypeError, KeyError, AttributeError, OSError, RecursionError, RecordError) as exc:
            diagnostics.append(dict(source_index=source_index, error=type(exc).__name__, message=str(exc)))
    bundle = dict(schema=1, sources=sources, records=generic, measurements=measurements,
                  definitions=specs, diagnostics=diagnostics, command_code=2 if diagnostics else 0)
    if selection_indices is not None:
        bundle['selection_indices'] = selection_indices
    budget = budget if budget is not None else Budget(64 * 1024 * 1024, 'output')
    output.mkdir(parents=True)
    write_json(output / 'export.json', bundle, budget)
    with output_stream(output / 'records.csv', budget) as stream:
        writer = csv.writer(stream)
        writer.writerow(['run_id_json', 'case_id_json', 'sequence', 'name_json', 'data_json'])
        for row in generic:
            writer.writerow([encoded(row[key]) for key in ('run_id', 'case_id', 'sequence', 'name', 'data')])
    if config is not None:
        keys = ('run_id', 'case_id', 'sequence', 'series', 'unit', 'state', 'raw_value', 'value', 'error')
        with output_stream(output / 'measurements.csv', budget) as stream:
            writer = csv.writer(stream)
            writer.writerow([key + '_json' for key in keys])
            for row in measurements:
                writer.writerow([encoded(row[key]) if key in row else '' for key in keys])
    return bundle
