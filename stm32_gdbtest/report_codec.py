"""Lossless blocks of completed report rows; no GDB access or value coercion."""
import copy
import hashlib
import json
from collections import Counter

MAX_ROWS = 128

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')

def pack(rows):
    if type(rows) is not list or len(rows) > MAX_ROWS or any(type(r) is not dict for r in rows):
        raise ValueError('rows')
    candidates = Counter(canonical(v) for row in rows for v in row.values())
    atoms = [json.loads(raw) for raw, n in candidates.items() if n > 1 and len(raw) >= 24]
    refs = {canonical(value): i for i, value in enumerate(atoms)}
    shapes, shape_ids, runs = [], {}, []
    for row in rows:
        keys = tuple(row)
        if keys not in shape_ids:
            shape_ids[keys] = len(shapes); shapes.append(list(keys))
        cells = []
        for value in row.values():
            ref = refs.get(canonical(value))
            cells.append(['v', copy.deepcopy(value)] if ref is None else ['r', ref])
        encoded = [shape_ids[keys], cells]
        if runs and canonical(runs[-1][1]) == canonical(encoded):
            runs[-1][0] += 1
        else:
            runs.append([1, encoded])
    return dict(schema=1, count=len(rows), shapes=shapes, atoms=atoms, runs=runs)

def expand(data, maximum=MAX_ROWS, maximum_bytes=64 * 1024 * 1024):
    if (type(data) is not dict or set(data) != {'schema','count','shapes','atoms','runs'}
            or type(data['schema']) is not int or data['schema'] != 1
            or type(data['count']) is not int or not 0 <= data['count'] <= maximum):
        raise ValueError('envelope')
    shapes, atoms = data['shapes'], data['atoms']
    if type(shapes) is not list or type(atoms) is not list or type(data['runs']) is not list:
        raise ValueError('tables')
    for keys in shapes:
        if type(keys) is not list or any(type(k) is not str for k in keys) or len(set(keys)) != len(keys):
            raise ValueError('shape')
    result=[]
    expanded_bytes = 0
    for block in data['runs']:
        if type(block) is not list or len(block) != 2:
            raise ValueError('run')
        repeat, encoded = block
        if type(repeat) is not int or repeat <= 0 or len(result) + repeat > data['count']:
            raise ValueError('expansion limit')
        if type(encoded) is not list or len(encoded) != 2:
            raise ValueError('row')
        shape, cells = encoded
        if type(shape) is not int or not 0 <= shape < len(shapes):
            raise ValueError('shape ref')
        if type(cells) is not list or len(cells) != len(shapes[shape]):
            raise ValueError('arity')
        values=[]
        for cell in cells:
            if type(cell) is not list or len(cell) != 2:
                raise ValueError('cell')
            tag,value=cell
            if tag == 'r':
                if type(value) is not int or not 0 <= value < len(atoms): raise ValueError('atom ref')
                value=atoms[value]
            elif tag != 'v': raise ValueError('cell tag')
            values.append(value)
        row = dict(zip(shapes[shape], values))
        expanded_bytes += len(canonical(row)) * repeat
        if expanded_bytes > maximum_bytes:
            raise ValueError("expanded report byte limit")
        for _ in range(repeat): result.append(copy.deepcopy(row))
    if len(result) != data['count']: raise ValueError('count')
    return result

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()
