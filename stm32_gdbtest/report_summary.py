"""Derived views of validated evidence. Never calls GDB or changes a verdict."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from stm32_gdbtest import report_data
from stm32_gdbtest.result_capture import read as read_records

MAX_GROUPS = 100
MAX_REFERENCES = 20
MAX_BYTES = 1024 * 1024


def digest(path, maximum):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('summary source must not be a symlink')
    h = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        while raw := stream.read(65536):
            total += len(raw)
            if total > maximum:
                raise ValueError('summary source exceeds limit')
            h.update(raw)
    return h.hexdigest()


def label(value):
    text = value if type(value) is str else json.dumps(value, sort_keys=True, allow_nan=False)
    return dict(text=text[:256], value_type=type(value).__name__, shortened=len(text) > 256,
                sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())


def ref(collection, index, source='result.json'):
    return dict(source=source, collection=collection, index=index)


def grouped(rows, keys, collection, source='result.json'):
    """Exact counts, bounded presentation; omitted groups remain in the source."""
    groups = {}
    total = failed = unknown = 0
    for index, row in enumerate(rows):
        if type(row) is not dict:
            raise ValueError('summary row must be an object')
        total += 1
        failed += row.get('passed') is False
        if collection == 'checks' and type(row.get('passed')) is not bool:
            unknown += 1
        identity = json.dumps([row.get(k) for k in keys], sort_keys=True, allow_nan=False)
        group = groups.get(identity)
        if group is None:
            group = groups[identity] = dict(key={k: label(row.get(k)) for k in keys},
                count=0, failed=0, references=[], failure_references=[], expectations=set())
        group['count'] += 1
        group['failed'] += row.get('passed') is False
        if len(group['references']) < MAX_REFERENCES:
            group['references'].append(ref(collection, index, source))
        if row.get('passed') is False and len(group['failure_references']) < MAX_REFERENCES:
            group['failure_references'].append(ref(collection, index, source))
        if collection == 'checks':
            value = json.dumps(row.get('expected'), sort_keys=True, allow_nan=False)
            group['expectations'].add(value)
    visible = []
    # Failed groups come first, without hiding how many other groups were omitted.
    for group in sorted(groups.values(), key=lambda g: not bool(g['failed']))[:MAX_GROUPS]:
        expectations = group.pop('expectations')
        group['different_expectations'] = len(expectations) > 1
        failures = group.pop('failure_references')
        references = failures + [r for r in group['references'] if r not in failures]
        group['references'] = references[:MAX_REFERENCES]
        group['references_omitted'] = group['count'] - len(group['references'])
        group['failure_references_omitted'] = group['failed'] - len(failures)
        if collection != 'checks':
            group['failed'] = None
            group['failure_references_omitted'] = None
        visible.append(group)
    return dict(total=total, failed=failed if collection == 'checks' else None,
                outcome_classification='check_verdict' if collection == 'checks' else 'see_source_events_and_diagnostics',
                unclassified=unknown, groups_total=len(groups),
                groups_omitted=len(groups)-len(visible), groups=visible)


def execution(records):
    operations = {}
    outcomes = {}
    windows = {}
    first = last = None
    count = unknown = 0
    for row in records:
        if row['name'] != 'execution':
            continue  # User measurements are never aggregated implicitly.
        data = row['data']
        count += 1
        location = dict(source='records.json', sequence=row['sequence'])
        if type(data) is not dict:
            unknown += 1
            continue
        error = data.get('error')
        detail = error if type(error) is dict else data
        op = detail.get('operation')
        outcome = 'error' if error is not None else data.get('outcome')
        if op not in ('resume','wait','halt','reach','step','until','finish','ret','call','boot') or outcome not in ('started','stopped','exited','timeout','error'):
            unknown += 1
            continue
        operations[op] = operations.get(op, 0) + 1
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        event = dict(operation=op, outcome=outcome, reference=location)
        if first is None:
            first = event
        last = event
        stop = detail.get('stop', {})
        generation = detail.get('generation', stop.get('generation') if type(stop) is dict else None)
        if type(generation) is not int or generation < 0:
            unknown += 1
            continue
        window = windows.setdefault(generation, dict(generation=generation, state='unknown',
                                                   opened=False, timeouts=0, last=location))
        window['last'] = location
        if outcome == 'started':
            if window['opened']:
                unknown += 1
                window['state'] = 'unknown'
            else:
                window.update(opened=True, state='open')
        elif outcome in ('stopped', 'exited'):
            window['state'] = 'closed'
        elif outcome == 'timeout':
            window['timeouts'] += 1  # Never closes or opens a window.
        else:
            window['state'] = 'unknown'
    states = {name: sum(w['state'] == name for w in windows.values())
              for name in ('open','closed','unknown')}
    return dict(total=count, operations=operations, outcomes=outcomes, first=first, last=last,
                unresolved=unknown, states=states, windows=list(windows.values())[:MAX_GROUPS],
                windows_omitted=max(0,len(windows)-MAX_GROUPS))


def build(result_path):
    """Recompute from saved files, validating each source before use."""
    path = Path(result_path)
    before = digest(path, report_data.FILE_BYTES)
    report = report_data.read(path, materialize=False)
    if type(report.get('id')) is not str or not report['id'] or report.get('status') not in ('PASS','FAIL','ERROR','SKIP'):
        raise ValueError('source is not an identified scenario result')
    issues = []
    sources = [dict(path=path.name, sha256=before, state='verified')]
    collections = {}
    for name, keys in [('checks',('name','kind')),('stops',('kind','signal')),
                       ('mutations',('operation','expression','path')),
                       ('evaluations',('operation',)),('executions',('operation','result')),
                       ('resets',('operation',))]:
        collections[name] = grouped(report.get(name, []), keys, name, path.name)
        collections[name]['availability'] = 'recorded' if name in report else 'not_recorded'
        if collections[name]['unclassified']:
            issues.append(name + ': unclassified outcomes')
    if 'checks' not in report:
        issues.append('checks collection not recorded')
    for field in ('report_storage_error','report_audit_error_count','execution_audit_error_count'):
        if report.get(field):
            issues.append(field)
    capture = report.get('capture', {})
    live = None
    if capture.get('status') == 'saved':
        try:
            data = read_records(path.parent, report, materialize=False)
            live = execution(data['records'])
            # Hash again after traversal; do not silently seal a changing source.
            actual = digest(path.parent/'records.json', 64*1024*1024)
            if actual != capture['sha256']:
                raise ValueError('records changed during summary')
            sources.append(dict(path='records.json', sha256=actual, state='verified'))
            if live['unresolved']:
                issues.append('execution events without sufficient structure/generation')
        except (ValueError, OSError, KeyError, TypeError) as error:
            live = None
            sources.append(dict(path='records.json', state='unavailable'))
            issues.append('records unavailable: '+str(error)[:256])
    else:
        sources.append(dict(path='records.json', state='unavailable'))
        issues.append('records not saved; execution history not verified')
    if digest(path, report_data.FILE_BYTES) != before:
        raise ValueError('result changed during summary')
    diagnostics = []
    for name in ('error','primary_error','teardown_error','warnings','artifact_error',
                 'report_storage_error','report_audit_errors','execution_audit_errors',
                 'execution_cleanup_error','execution_cleanup_audit_error','summary_error'):
        if name in report:
            diagnostics.append(dict(field=name, preview=label(report[name]),
                                    reference=dict(source=path.name,field=name)))
    return dict(schema=1, derived=True, analysis='partial' if issues else 'complete',
                issues=issues, sources=sources, verdicts={key: report.get(key) for key in
                ('id','run_id','mode','status','command_code','capture','cleanup','execution_cleanup')},
                collections=collections, execution=live, diagnostics=diagnostics,
                limits=dict(groups=MAX_GROUPS,references_per_group=MAX_REFERENCES),
                meaning='Presentation only; completeness is not DDTT applicability')


def write(result_path):
    path = Path(result_path)
    destination = path.with_name('summary.json')
    if path.resolve() == destination.resolve():
        raise ValueError('summary output must not replace its source')
    destination.unlink(missing_ok=True)  # A failed rebuild must not leave an old green view.
    data = build(path)
    raw = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('summary exceeds 1 MiB presentation budget')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.summary-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return data


def read(result_path):
    """Reject stale or edited derived views, even when source hashes look valid."""
    path = Path(result_path).with_name('summary.json')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES:
        raise ValueError('summary exceeds 1 MiB')
    data = json.loads(raw, object_pairs_hook=report_data.unique)
    from stm32_gdbtest.report_codec import canonical
    if canonical(data) != canonical(build(result_path)):
        raise ValueError('summary is stale, invalid or inconsistent with its sources')
    return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    print(json.dumps(read(args.result) if args.verify else write(args.result), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
