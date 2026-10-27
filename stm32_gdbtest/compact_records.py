"""Lossless MMIO journal encoding; user records never acquire internal semantics."""
import copy
import hashlib
import json

from stm32_gdbtest.records import Journal, RecordError
from stm32_gdbtest.configuration import MAXIMUMS_V2, QUERY_NODES


class CompactJournal(Journal):
    def __init__(self, **limits):
        super().__init__(**limits)
        self.definitions = {}
        self._pending = None

    def mmio_record(self, name, data):
        try:
            self._mmio_record(name, data)
        except RecordError as error:
            error.details['record_name'] = name[:128]
            raise

    def _mmio_record(self, name, data):
        self._logical_depth(data)
        if name == 'mmio.attempt':
            definition = {k: data[k] for k in ('original', 'effective', 'svd_sha256')}
            # Validate before encoding: no arbitrary Python conversion hooks.
            checked = self._copy(definition, 0, set(), [0, 0], '$definition')
            key = hashlib.sha256(json.dumps(checked, sort_keys=True, ensure_ascii=True,
                                           separators=(',', ':')).encode()).hexdigest()
            operation = len(self._entries) + 1
            event = dict(kind='mmio.attempt', operation_id=operation, definition=key,
                         payload={k: v for k, v in data.items() if k not in definition})
            added = key not in self.definitions
            budget = [self._nodes, self._text_bytes]
            if added:
                self._copy(key, 0, set(), budget, '$definitions.key')
                checked = self._copy(checked, 0, set(), budget, '$definitions.value')
            previous = self._nodes, self._text_bytes
            self._nodes, self._text_bytes = budget
            try:
                self._store(name, event)
            except BaseException:
                self._nodes, self._text_bytes = previous
                raise
            if added:
                self.definitions[key] = checked
            self._pending = operation
        elif name == 'mmio.result':
            if self._pending is None:
                raise ValueError('MMIO result without attempt')
            self._store(name, dict(kind='mmio.result', operation_id=self._pending, payload=data))
            self._pending = None
        else:
            raise ValueError('Unknown internal MMIO record')

    def record(self, name, data):
        # Validate logical depth/types/cycles before adding the internal envelope.
        if type(name) is not str or not name:
            raise RecordError('invalid_name', 'name must be a non-empty string')
        try:
            checked = self._copy(data, 0, set(), [0, 0], '$data')
            self._store(name, dict(kind='user', payload=checked))
        except RecordError as error:
            error.details['record_name'] = name[:128]
            raise

    def _logical_depth(self, value, depth=0):
        if depth > self._limits[2]:
            error = RecordError('limit_exceeded', 'logical depth limit exceeded', limit='depth')
            error.details.update(path='$data', maximum=self._limits[2], used=0,
                                 attempted=depth, attempted_lower_bound=False)
            raise error
        if type(value) is dict:
            for k, v in value.items():
                self._logical_depth(k, depth+1)
                self._logical_depth(v, depth+1)
        elif type(value) is list:
            for v in value:
                self._logical_depth(v, depth+1)

    def _store(self, name, event):
        limits = self._limits
        self._limits = (*limits[:2], limits[2]+2, *limits[3:])
        try:
            Journal.record(self, name, event)
        finally:
            self._limits = limits

    def iter_records(self, name=None):
        if name is not None and (type(name) is not str or not name):
            raise RecordError('invalid_name', 'filter must be None or a non-empty string')
        for entry in self._entries:
            if name is not None and entry['name'] != name:
                continue
            event = entry['data']
            data = dict(event['payload']) if event['kind'] == 'mmio.attempt' else event['payload']
            if event['kind'] == 'mmio.attempt':
                data.update(self.definitions[event['definition']])
            yield dict(sequence=entry['sequence'], name=entry['name'], data=copy.deepcopy(data))

    def records(self, name=None):
        validator = Journal(**dict(MAXIMUMS_V2, max_nodes=QUERY_NODES))
        for row in self.iter_records(name):
            try:
                validator.record(row['name'], row['data'])
            except RecordError as error:
                error.details['operation'] = 'records'
                error.details['scope'] = 'materialization'
                raise
            # Preserve the original sequence after filtering.
            validator._entries[-1]['sequence'] = row['sequence']
        return validator._entries

    def payload(self, run_id, case_id):
        # Borrowed read-only view for streaming serialization, never exposed by Target.records.
        return dict(schema=2, representation='compact', run_id=run_id, case_id=case_id,
                    definitions=self.definitions, records=self._entries)


def decode(data):
    """Validate compact references and budgets, then expose detached logical rows lazily."""
    if set(data) != {'schema', 'representation', 'run_id', 'case_id', 'definitions', 'records'}:
        raise ValueError('invalid compact envelope')
    if data['representation'] != 'compact' or type(data['definitions']) is not dict or type(data['records']) is not list:
        raise ValueError('invalid compact representation')
    journal = CompactJournal(**MAXIMUMS_V2)
    budget = [0, 0]
    for key, definition in data['definitions'].items():
        if type(key) is not str or type(definition) is not dict or set(definition) != {'original', 'effective', 'svd_sha256'}:
            raise ValueError('invalid definition')
        journal._copy(key, 0, set(), budget, '$definitions.key')
        journal._copy(definition, 0, set(), budget, '$definitions.value')
        expected = hashlib.sha256(json.dumps(definition, sort_keys=True, ensure_ascii=True,
                                            separators=(',', ':')).encode()).hexdigest()
        if key != expected:
            raise ValueError('definition hash mismatch')
    journal._nodes, journal._text_bytes = budget
    pending, used = None, set()
    for sequence, row in enumerate(data['records'], 1):
        if (type(row) is not dict or set(row) != {'sequence', 'name', 'data'}
                or type(row['sequence']) is not int or row['sequence'] != sequence):
            raise ValueError('invalid sequence')
        event = row['data']
        if type(event) is not dict:
            raise ValueError('invalid event')
        kind = event.get('kind')
        fields = {'kind', 'payload'}
        if kind in ('mmio.attempt', 'mmio.result'):
            fields.add('operation_id')
            if type(event.get('operation_id')) is not int or row['name'] != kind or type(event.get('payload')) is not dict:
                raise ValueError('invalid MMIO event')
            payload = event['payload']
            if (payload.get('operation') not in ('read', 'write')
                    or type(payload.get('name')) is not str or not payload['name']):
                raise ValueError('invalid MMIO identity')
            if kind == 'mmio.attempt':
                fields.add('definition')
                ref = event.get('definition')
                if type(ref) is not str or ref not in data['definitions'] or event['operation_id'] != sequence:
                    raise ValueError('invalid MMIO reference')
                if {'original', 'effective', 'svd_sha256'} & set(event['payload']):
                    raise ValueError('shadowed definition')
                expected = {'operation', 'name', 'override', 'reason', 'allow_effects'}
                if payload['operation'] == 'write':
                    expected.add('value')
                if (set(payload) != expected or type(payload['override']) is not bool
                        or type(payload['allow_effects']) is not bool
                        or (payload['reason'] is not None and type(payload['reason']) is not str)):
                    raise ValueError('invalid attempt payload')
                used.add(ref)
                pending = (sequence, event['payload'].get('operation'), event['payload'].get('name'))
            elif pending != (event['operation_id'], event['payload'].get('operation'), event['payload'].get('name')):
                raise ValueError('unmatched MMIO result')
            else:
                expected = {'operation', 'name', 'status'}
                if payload.get('status') == 'ERROR':
                    expected.add('effect')
                    if payload.get('effect') != 'unknown':
                        raise ValueError('invalid error effect')
                elif payload.get('status') == 'completed':
                    expected.add('result')
                else:
                    raise ValueError('invalid result status')
                if set(payload) != expected:
                    raise ValueError('invalid result payload')
                pending = None
        elif kind != 'user':
            raise ValueError('unsupported event kind')
        if set(event) != fields:
            raise ValueError('invalid event fields')
        journal._store(row['name'], event)
    if used != set(data['definitions']):
        raise ValueError('unused definition')
    journal.definitions = data['definitions']
    for row in journal.iter_records():
        journal._logical_depth(row['data'])
    return journal
