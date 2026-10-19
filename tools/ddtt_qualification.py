"""DDTT applicability from immutable, externally measured conditions (ТЗ 5.28)."""
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result


def number(value):
    try:
        return type(value) in (float, int) and math.isfinite(value)
    except OverflowError:
        return False


def validate(mapping):
    """Policy is reviewed before execution; errors cannot silently disable gates."""
    if mapping.get('schema', 1) == 1:
        if 'qualification' in mapping or any('requires' in p or 'required' in p for p in mapping['points']):
            raise ValueError('Qualification requires map schema 2')
        return
    q = mapping.get('qualification')
    if not isinstance(q, dict) or set(q) != {'context', 'conditions'}:
        raise ValueError('Expected qualification context and conditions')
    context = q['context']
    if set(context) != {'instance', 'environment', 'elf_sha256', 'inputs_sha256'}:
        raise ValueError('Invalid qualification context')
    if not isinstance(context['instance'], str) or not context['instance']:
        raise ValueError('Instance identity required')
    if context['environment'] != mapping.get('environment', 'hardware') or context['elf_sha256'] != mapping['elf_sha256']:
        raise ValueError('Qualification context differs from map')
    if not re.fullmatch('[0-9a-f]{64}', context['inputs_sha256']):
        raise ValueError('Expected inputs fingerprint')
    conditions = q['conditions']
    if not isinstance(conditions, dict):
        raise ValueError('Expected conditions table')
    for key, rule in conditions.items():
        if not re.fullmatch('[a-z][a-z0-9_]*', key):
            raise ValueError('Invalid condition identifier')
        if not isinstance(rule, dict) or set(rule) - {'unit', 'min', 'max', 'max_age_s', 'kind'} or not {'unit', 'min', 'max', 'max_age_s'} <= set(rule):
            raise ValueError('Expected numeric interval, unit and freshness')
        if rule.get('kind', 'measurement') not in ('measurement', 'capability'):
            raise ValueError('Invalid condition kind')
        if rule.get('kind') == 'capability' and (rule['unit'] != 'present' or rule['min'] != 1 or rule['max'] != 1):
            raise ValueError('Capability expects presence=1')
        if not isinstance(rule['unit'], str) or not rule['unit']:
            raise ValueError('Explicit units required')
        if not all(number(rule[k]) for k in ('min', 'max', 'max_age_s')) or rule['min'] > rule['max'] or rule['max_age_s'] <= 0:
            raise ValueError('Invalid condition bounds')
    for point in mapping['points']:
        required = point.get('requires')
        if not isinstance(required, list) or any(not isinstance(k, str) or k not in conditions for k in required) or len(set(required)) != len(required):
            raise ValueError('Each point needs explicit, unique condition references')
        if type(point.get('required', True)) is not bool:
            raise ValueError('required must be boolean')


def bind(result, snapshot, destination=None):
    """External organizer binds an existing snapshot, without altering result.json."""
    result = Path(result)
    admission = dict(schema=1, result_sha256=digest(result.read_bytes()),
                     snapshot_sha256=digest(canonical(snapshot)), snapshot=snapshot)
    destination = Path(destination) if destination else result.with_name('admission.json')
    # Нельзя незаметно заменить снимок допуска задним числом.
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(admission, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return admission


def evaluate(mapping, point, result, path):
    """No transport. Invalid/missing evidence never grants admission."""
    def outcome(status, reason, conditions=None, fingerprint=None):
        return dict(status=status, reason=reason, conditions=conditions or [], snapshot_sha256=fingerprint)
    if not point['requires']:
        return outcome('NOT_REQUIRED', 'independent_assertion')
    if path is None:
        return outcome('UNKNOWN', 'no_attempt')
    try:
        admission = json.loads(Path(path).with_name('admission.json').read_text(encoding='utf-8'))
        if set(admission) != {'schema', 'result_sha256', 'snapshot_sha256', 'snapshot'} or type(admission['schema']) is not int or admission['schema'] != 1:
            return outcome('UNKNOWN', 'invalid_admission')
        if admission['result_sha256'] != digest(Path(path).read_bytes()):
            return outcome('UNKNOWN', 'result_mismatch')
        snapshot = admission['snapshot']
        fingerprint = digest(canonical(snapshot))
        if fingerprint != admission['snapshot_sha256']:
            return outcome('UNKNOWN', 'snapshot_mismatch')
        if set(snapshot) != {'schema', 'context', 'measurements'} or type(snapshot['schema']) is not int or snapshot['schema'] != 1:
            return outcome('UNKNOWN', 'invalid_snapshot')
        if snapshot['context'] != mapping['qualification']['context']:
            return outcome('UNKNOWN', 'context_mismatch', fingerprint=fingerprint)
        if result.get('mode') != snapshot['context']['environment'] or result.get('elf_sha256') != snapshot['context']['elf_sha256']:
            return outcome('UNKNOWN', 'result_context_mismatch', fingerprint=fingerprint)
        start = stamp(result['started_utc'])
        duration = result['duration_s']
        if not number(duration) or duration < 0:
            return outcome('UNKNOWN', 'invalid_duration', fingerprint=fingerprint)
        end = start + timedelta(seconds=duration)
        measurements = snapshot['measurements']
        if not isinstance(measurements, list):
            return outcome('UNKNOWN', 'invalid_measurements', fingerprint=fingerprint)
        checks = []
        for key in point['requires']:
            selected = [m for m in measurements if m.get('condition') == key]
            status, reason = 'UNKNOWN', 'missing_or_conflicting_measurements'
            if len(selected) == 1:
                m = selected[0]
                rule = mapping['qualification']['conditions'][key]
                needed = {'condition', 'value', 'uncertainty', 'unit', 'observed_utc', 'valid_until', 'invalidated_utc', 'method', 'evidence_sha256'}
                if set(m) != needed:
                    reason = 'invalid_measurement'
                elif m['method'] != 'measured' or not isinstance(m['evidence_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', m['evidence_sha256']):
                    reason = 'not_measured'
                elif not number(m['value']) or not number(m['uncertainty']) or m['uncertainty'] < 0 or m['unit'] != rule['unit']:
                    reason = 'invalid_value_or_unit'
                elif rule.get('kind') == 'capability' and (m['value'] not in (0, 1) or m['uncertainty'] != 0):
                    reason = 'invalid_capability'
                elif not stamp(m['observed_utc']) <= start <= end <= stamp(m['valid_until']) or (end - stamp(m['observed_utc'])).total_seconds() > rule['max_age_s']:
                    reason = 'stale_or_future'
                elif m['invalidated_utc'] is not None and stamp(m['invalidated_utc']) <= end:
                    reason = 'invalidated'
                else:
                    lo, hi = m['value'] - m['uncertainty'], m['value'] + m['uncertainty']
                    if rule['min'] <= lo <= hi <= rule['max']:
                        status, reason = 'APPLICABLE', 'within_bounds'
                    elif hi < rule['min'] or lo > rule['max']:
                        status, reason = 'VIOLATED', 'outside_bounds'
                        if rule.get('kind') == 'capability' and not point.get('required', True):
                            status, reason = 'NOT_APPLICABLE', 'optional_capability_absent'
                    else:
                        reason = 'uncertainty_overlaps_boundary'
            checks.append(dict(condition=key, status=status, reason=reason))
        states = {c['status'] for c in checks}
        status = 'VIOLATED' if 'VIOLATED' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'NOT_APPLICABLE' if 'NOT_APPLICABLE' in states else 'APPLICABLE'
        return outcome(status, 'condition_evaluation', checks, fingerprint)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return outcome('UNKNOWN', 'invalid_or_missing_admission')


def apply(mapping, point, result, path, row):
    row['raw_state'] = row['state']
    row['raw_reason'] = row['reason']
    row['applicability'] = evaluate(mapping, point, result, path)
    if row['applicability']['status'] not in ('APPLICABLE', 'NOT_REQUIRED'):
        row['state'] = 'UNKNOWN'
        row['reason'] = 'qualification_' + row['applicability']['status'].lower()


def summary(rows):
    required = [p for p in rows if p.get('required', True)]
    blocked = sum(p['applicability']['status'] not in ('APPLICABLE', 'NOT_REQUIRED') for p in required)
    return dict(required=len(required), blocked=blocked,
                accepted=bool(required) and all(p['state'] == 'CONFIRMED' for p in required))
