"""Strict evidence accounting, independent of event storage and presentation."""
import json
from stm32_gdbtest.errors import error_summary

COLLECTIONS = ('checks', 'stops', 'mutations', 'evaluations', 'executions', 'resets')
MAX_DIAGNOSTICS = 16
MAX_DIAGNOSTIC_BYTES = 65536


def state(saved=0):
    return dict(state='complete', attempted=saved, saved=saved, lost=0,
                first_lost=None, last_lost=None)


def initialize(report):
    if 'evidence' not in report:
        report['evidence'] = dict(schema=1, policy='error',
            stores={name: state(len(report.get(name, []))) for name in COLLECTIONS},
            diagnostics=[], diagnostics_total=0, diagnostics_omitted=0)
        report['check_accounting'] = dict(total=0, failed=0, unclassified=0)
        for row in report.get('checks', []):
            check(report, row)
    return report['evidence']


def check(report, row):
    counts = report['check_accounting']
    counts['total'] += 1
    passed = row.get('passed')
    if passed is False:
        counts['failed'] += 1
    elif passed is not True:
        counts['unclassified'] += 1


def begin(report, store):
    meta = initialize(report)['stores'].setdefault(store, state())
    meta['attempted'] += 1
    return meta


def diagnostic(report, store, error):
    meta = initialize(report)
    meta['diagnostics_total'] += 1
    summary = error_summary(error)
    for key, value in list(summary.items()):
        if type(value) is int and value.bit_length() > 256:
            summary[key] = '<integer exceeds diagnostic budget>'
    detail = dict(store=store, error=summary)
    rows = meta['diagnostics']
    size = len(json.dumps(rows + [detail], ensure_ascii=True).encode('utf-8'))
    if len(rows) < MAX_DIAGNOSTICS and size <= MAX_DIAGNOSTIC_BYTES:
        rows.append(detail)
    meta['diagnostics_omitted'] = meta['diagnostics_total'] - len(rows)


def lost(report, store, meta, error):
    meta['state'] = 'unavailable'
    meta['lost'] += 1
    if meta['first_lost'] is None:
        meta['first_lost'] = meta['attempted']
    meta['last_lost'] = meta['attempted']
    diagnostic(report, store, error)


def journal(report, callback, name, data):
    meta = initialize(report)["stores"].setdefault("records", state())
    truncate = getattr(getattr(callback, '__self__', None), 'on_limit', 'error') == 'truncate'
    if truncate:
        # Validate logical values independently of exhausted cumulative storage.
        # Hard resource ceilings still apply and are never silently suppressed.
        callback.__self__.validate_record(name, data)
        report['evidence'].update(schema=2, policy='journal-truncate')
        if meta['state'] == 'truncated':
            meta['attempted'] += 1
            meta['lost'] += 1
            meta['last_lost'] = meta['attempted']
            return
    try:
        result = callback(name, data)
    except Exception as error:
        # Invalid inputs are refused before evidence admission, not missing observations.
        if (getattr(error, 'code', None) == 'limit_exceeded' and
                getattr(error, 'limit', None) in ('records', 'nodes', 'text_bytes')) or not hasattr(error, 'code'):
            meta['attempted'] += 1
            lost(report, 'records', meta, error)
            if truncate and getattr(error, 'code', None) == 'limit_exceeded' and meta['lost'] == 1:
                meta['state'] = 'truncated'
                return
        raise
    meta['attempted'] += 1
    meta['saved'] += 1
    return result


def unavailable(report):
    return any(s['state'] != 'complete' for s in report.get('evidence', {}).get('stores', {}).values())


def storage_failed(report):
    return any(s['state'] == 'unavailable' for s in report.get('evidence', {}).get('stores', {}).values())


def discard_collections(report, error):
    """A serialization fallback contains no collection rows; retain attempted counts."""
    meta = report.get('evidence')
    if meta is None:
        return
    for name in COLLECTIONS:
        item = meta['stores'][name]
        if item['attempted']:
            item.update(state='unavailable', saved=0, lost=item['attempted'],
                        first_lost=1, last_lost=item['attempted'])
    diagnostic(report, 'result', error)


def validate(report, records_count=None):
    """Legacy results remain readable; absence is not a completeness assertion."""
    meta = report.get('evidence')
    if meta is None:
        return
    if (type(meta) is not dict or set(meta) != {'schema','policy','stores','diagnostics',
            'diagnostics_total','diagnostics_omitted'} or type(meta['schema']) is not int
            or (meta['schema'], meta['policy']) not in ((1, 'error'), (2, 'journal-truncate'))):
        raise ValueError('invalid strict evidence metadata')
    stores = meta['stores']
    if type(stores) is not dict or not set(COLLECTIONS) <= set(stores) or set(stores) - set(COLLECTIONS + ('records',)):
        raise ValueError('invalid evidence stores')
    for name, item in stores.items():
        if type(item) is not dict or set(item) != set(state()):
            raise ValueError('invalid evidence counters')
        for key in ('attempted','saved','lost'):
            if type(item[key]) is not int or item[key] < 0:
                raise ValueError('invalid evidence count')
        if item['attempted'] != item['saved'] + item['lost']:
            raise ValueError('evidence count mismatch')
        if item['lost'] == 0:
            if item['state'] != 'complete' or item['first_lost'] is not None or item['last_lost'] is not None:
                raise ValueError('invalid complete evidence')
        elif (item['state'] not in ('unavailable', 'truncated') or type(item['first_lost']) is not int
              or type(item['last_lost']) is not int or not 1 <= item['first_lost'] <= item['last_lost'] <= item['attempted']
              or item['lost'] > item['last_lost'] - item['first_lost'] + 1
              or (item['lost'] == 1 and item['first_lost'] != item['last_lost'])):
            raise ValueError('invalid lost evidence range')
        if item['state'] == 'truncated' and (meta['schema'] != 2 or name != 'records'
                or item['first_lost'] != item['saved'] + 1 or item['last_lost'] != item['attempted']):
            raise ValueError('invalid truncated prefix')
        count = records_count if name == 'records' else len(report.get(name, []))
        if count is not None and item['saved'] != count:
            raise ValueError('saved evidence count mismatch: ' + name)
    rows = meta['diagnostics']
    if (type(rows) is not list or len(rows) > MAX_DIAGNOSTICS
            or len(json.dumps(rows, ensure_ascii=True).encode('utf-8')) > MAX_DIAGNOSTIC_BYTES):
        raise ValueError('diagnostic reserve exceeded')
    for row in rows:
        if type(row) is not dict or set(row) != {'store','error'} or row['store'] not in COLLECTIONS + ('records','result') or type(row['error']) is not dict:
            raise ValueError('invalid evidence diagnostic')
    for key in ('diagnostics_total','diagnostics_omitted'):
        if type(meta[key]) is not int or meta[key] < 0:
            raise ValueError('invalid diagnostic count')
    if meta['diagnostics_total'] != len(rows) + meta['diagnostics_omitted']:
        raise ValueError('diagnostic count mismatch')
    counts = report.get('check_accounting')
    if (type(counts) is not dict or set(counts) != {'total','failed','unclassified'}
            or any(type(v) is not int or v < 0 for v in counts.values())
            or counts['total'] != stores['checks']['attempted']
            or counts['failed'] + counts['unclassified'] > counts['total']):
        raise ValueError('invalid independent check accounting')
    failed = unclassified = 0
    for row in report.get('checks', []):
        failed += row.get('passed') is False
        unclassified += type(row.get('passed')) is not bool
    lost_checks = stores['checks']['lost']
    if not (failed <= counts['failed'] <= failed + lost_checks and
            unclassified <= counts['unclassified'] <= unclassified + lost_checks
            and counts['failed'] + counts['unclassified'] - failed - unclassified <= lost_checks):
        raise ValueError('check accounting differs from evidence')
