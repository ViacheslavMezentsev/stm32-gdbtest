"""Standalone campaign summaries; evidence integrity is never a scenario verdict."""

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import tempfile

from stm32_gdbtest.result_files import Budget, ownership, output_stream, write_json
from stm32_gdbtest.report_style import CSS, CONTROLS, SCRIPT

VERDICTS = ('PASS', 'FAIL', 'ERROR', 'SKIP', 'UNKNOWN')


def export_counts(index, exported):
    """Join optional export only when identities and source fingerprints agree."""
    counts = {entry['selection_index']: dict(records=0, measurements=0, diagnostics=[]) for entry in index['runs']}
    if exported is None:
        return None
    fields = {'schema', 'sources', 'records', 'measurements', 'definitions', 'diagnostics', 'command_code', 'selection_indices'}
    if (type(exported) is not dict or set(exported) != fields or type(exported['schema']) is not int
            or exported['schema'] != 1 or type(exported['command_code']) is not int or exported['command_code'] not in (0, 2)
            or any(type(exported[k]) is not list for k in fields - {'schema', 'command_code'})):
        raise ValueError('invalid export envelope')
    selected = exported['selection_indices']
    expected = [entry['selection_index'] for entry in index['runs'] if entry['mode'] != 'prepare']
    if any(type(i) is not int for i in selected) or selected != expected:
        raise ValueError('export selection differs from index')
    by_id = {}
    for source in exported['sources']:
        if type(source) is not dict or type(source.get('source_index')) is not int or not 0 <= source['source_index'] < len(selected):
            raise ValueError('invalid export source')
        number = selected[source['source_index']]
        entry = index['runs'][number]
        if (source.get('run_id') != entry['run_id'] or source.get('case_id') != entry['case_id']
                or entry['run_id'] in by_id or entry['run_id'] is None):
            raise ValueError('export identity differs from index')
        for role, field in [('result', 'result_sha256'), ('records', 'records_sha256')]:
            artifacts = [a for a in entry['artifacts'] if a['role'] == role]
            if len(artifacts) != 1 or artifacts[0].get('sha256') is None or artifacts[0]['sha256'] != source.get(field):
                raise ValueError('export fingerprint differs from index')
        by_id[entry['run_id']] = number
    sequences = {run_id: {} for run_id in by_id}
    for field in ('records', 'measurements'):
        for row in exported[field]:
            if type(row) is not dict or type(row.get('run_id')) is not str or row['run_id'] not in by_id:
                raise ValueError('export row has no matching source')
            number = by_id[row['run_id']]
            if row.get('case_id') != index['runs'][number]['case_id']:
                raise ValueError('export row case mismatch')
            sequence = row.get('sequence')
            if type(sequence) is not int or sequence < 1:
                raise ValueError('invalid export sequence')
            if field == 'records':
                if (sequence in sequences[row['run_id']] or type(row.get('name')) is not str
                        or not row['name'] or 'data' not in row):
                    raise ValueError('invalid generic record')
                sequences[row['run_id']][sequence] = row['name']
            elif (sequences[row['run_id']].get(sequence) != row.get('record')
                    or row.get('state') not in ('value', 'null', 'missing', 'error')):
                raise ValueError('projection has no matching record')
            counts[number][field] += 1
    for run_id, number in by_id.items():
        expected_count = (index['runs'][number]['capture'] or {}).get('count')
        if (type(expected_count) is not int or expected_count != counts[number]['records']
                or sorted(sequences[run_id]) != list(range(1, expected_count + 1))):
            raise ValueError('export record count differs from capture')
    diagnosed = set()
    for diagnostic in exported['diagnostics']:
        if (type(diagnostic) is not dict or type(diagnostic.get('source_index')) is not int
                or not 0 <= diagnostic['source_index'] < len(selected)):
            raise ValueError('invalid export diagnostic source')
        number = selected[diagnostic['source_index']]
        counts[number]['diagnostics'].append(diagnostic)
        diagnosed.add(number)
    if set(selected) - set(by_id.values()) - diagnosed:
        raise ValueError('export omitted a selected source without a diagnostic')
    return counts


def summarize(index, integrity, exported=None):
    counts = export_counts(index, exported)
    checks = integrity['artifacts']
    offset = len(index['packages'])
    rows = []
    for entry in index['runs']:
        current = checks[offset:offset + len(entry['artifacts'])]
        offset += len(entry['artifacts'])
        package = entry['package']
        if package is not None:
            current = current + [checks[i] for i, artifact in enumerate(index['packages'])
                                 if artifact['expected_sha256'] == package['sha256']]
        problems = [a for a in current if a['state'] != 'ok']
        unchecked_package = package is not None and not package['artifacts']
        state = ('issues' if any(a['state'] in ('missing', 'changed') for a in problems) else
                 'unverified' if problems or not current or unchecked_package else 'ok')
        original = entry['verdict']
        rows.append(dict(entry, verdict=original if original in VERDICTS else 'UNKNOWN',
                         original_verdict=original, mode=entry['mode'] or 'unknown',
                         integrity=state, current_artifacts=current,
                         export=None if counts is None or entry['mode'] == 'prepare' else counts[entry['selection_index']]))
    groups = {}
    for mode in sorted({row['mode'] for row in rows}):
        subset = [row for row in rows if row['mode'] == mode]
        verdicts = Counter(row['verdict'] for row in subset)
        groups[mode] = dict(total=len(subset), verdicts={v: verdicts[v] for v in VERDICTS},
                            command_nonzero=sum(r['command_code'] in (1, 2) for r in subset),
                            command_unknown=sum(r['command_code'] is None for r in subset),
                            capture_errors=sum((r['capture'] or {}).get('status') == 'error' for r in subset),
                            integrity_issues=sum(r['integrity'] == 'issues' for r in subset))
    code = max(index['command_code'], integrity['command_code'], exported['command_code'] if exported else 0)
    return dict(schema=1, campaign_id=index['campaign_id'], name=index['name'],
                generated_utc=datetime.now(timezone.utc).isoformat(), aggregate_verdict=None,
                command_code=code, index_code=index['command_code'], integrity_code=integrity['command_code'],
                export_code=exported['command_code'] if exported else None, counts=groups, runs=rows)


def html_chunks(summary, theme):
    def text(value):
        return escape('—' if value is None else str(value), quote=True)

    yield '<!doctype html><html lang="ru" data-theme="' + theme + '"><head><meta charset="utf-8">'
    yield '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Campaign report</title><style>' + CSS + '</style></head><body>'
    yield '<header><strong>stm32-gdbtest</strong> · Сводка запусков / Campaign report</header><main>'
    yield CONTROLS
    yield '<section class="hero"><h1>' + text(summary['name']) + '</h1><p class="muted expert">' + text(summary['campaign_id']) + '</p>'
    yield '<p>Проверено / Checked: ' + text(summary['generated_utc']) + '</p></section>'
    yield '<div class="note">Все попытки сохранены. Общий PASS не вычисляется.<br>All attempts retained; no aggregate verdict.</div>'
    yield '<p>Код отчётной команды / Report command: <strong>' + text(summary['command_code']) + '</strong><span class="expert"> · index: ' + text(summary['index_code'])
    yield ' · integrity: ' + text(summary['integrity_code']) + ' · export: ' + text(summary['export_code']) + '</span></p>'
    yield '<p class="muted">Целостность проверена при генерации; это не мониторинг. Prepare не подтверждает работу MCU.<br>'
    yield 'Integrity is checked at generation time, not monitored. Prepare is not MCU execution evidence.</p>'
    for mode, group in summary['counts'].items():
        yield '<h2>' + text(mode) + ' · ' + text(group['total']) + '</h2><div class="cards">'
        for verdict, count in group['verdicts'].items():
            yield '<div class="card ' + verdict + '">' + verdict + '<strong>' + text(count) + '</strong></div>'
        yield '</div><p class="muted">Command ≠ 0: ' + text(group['command_nonzero']) + ' · Capture error: ' + text(group['capture_errors'])
        yield ' · Integrity issues: ' + text(group['integrity_issues']) + '</p><div class="scroll"><table><thead><tr>'
        for title in ('Стенд / Stand', 'Сценарий и попытка / Case and attempt', 'Исход / Verdict', 'Код / Command',
                      'Журнал / Capture', 'Целостность / Integrity', 'Данные / Data', 'Подробности / Details'):
            yield '<th scope="col"' + (' class="expert"' if title == 'Подробности / Details' else '') + '>' + title + '</th>'
        yield '</tr></thead><tbody>'
        for row in summary['runs']:
            if row['mode'] != mode:
                continue
            capture = row['capture'] or {}
            exported = row['export']
            data = '—' if exported is None else str(exported['records']) + ' records / ' + str(exported['measurements']) + ' values'
            yield '<tr><td>' + text(row['stand']) + '</td><td>' + text(row['case_id']) + '<small class="expert">' + text(row['run_id']) + '</small></td>'
            yield '<td class="' + row['verdict'] + '">' + row['verdict'] + '</td><td>' + text(row['command_code']) + '</td>'
            yield '<td>' + text(capture.get('status', 'unknown')) + '<small class="expert">' + text(capture.get('completion')) + '</small></td>'
            yield '<td class="' + row['integrity'] + '">' + row['integrity'] + '</td><td>' + text(data) + '</td>'
            yield '<td class="expert"><details><summary>Открыть / Open</summary><pre>' + text(json.dumps(row, ensure_ascii=False, indent=2)) + '</pre></details></td></tr>'
        yield '</tbody></table></div>'
    yield '</main><footer>SKIP ≠ PASS · UNKNOWN сохранён / retained · No network resources</footer><script>' + SCRIPT + '</script></body></html>'


def report(root, index, output, limits, *, exported=None, theme='auto'):
    from stm32_gdbtest.results import check
    if theme not in ('auto', 'light', 'dark'):
        raise ValueError('invalid report theme')
    integrity = check(root, index, limits)
    summary = summarize(index, integrity, exported)
    output = Path(output)
    with ownership(output), tempfile.TemporaryDirectory(prefix='.report-', dir=output.parent) as temporary:
        product = Path(temporary) / 'product'
        product.mkdir()
        budget = Budget(limits.output_bytes, 'report output')
        write_json(product / 'campaign.json', summary, budget)
        write_json(product / 'integrity.json', integrity, budget)
        with output_stream(product / 'campaign.html', budget) as stream:
            for chunk in html_chunks(summary, theme):
                stream.write(chunk)
        if output.exists() or output.is_symlink():
            raise FileExistsError(output)
        product.rename(output)
    return summary['command_code']
