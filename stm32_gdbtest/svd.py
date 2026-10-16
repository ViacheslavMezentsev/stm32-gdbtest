"""Bounded CMSIS-SVD subset for captured configuration (ТЗ 5.20.13).

No transport or MMIO operations. Unsupported descriptions fail closed.
"""
import copy
import hashlib
import re
import xml.etree.ElementTree as ET
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from types import MappingProxyType

class SvdError(ValueError):

    def __init__(self, code, detail=None):
        self.code = code
        self.stage = 'configuration'
        self.effect = 'none'
        self.detail = detail
        super().__init__(code + (': ' + str(detail) if detail else ''))
ACCESS = {'read-only', 'write-only', 'read-write', 'writeOnce', 'read-writeOnce'}
READ = {'clear', 'set', 'modify', 'modifyExternal'}
WRITE = {'oneToClear', 'oneToSet', 'oneToToggle', 'zeroToClear', 'zeroToSet', 'zeroToToggle', 'clear', 'set', 'modify'}
BUDGET = ContextVar('svd_budget')

def clone(node):
    BUDGET.get().consume('copies', sum((1 for _ in node.iter())))
    return copy.deepcopy(node)

@dataclass(frozen=True)
class Register:
    name: str
    address: int
    width: int
    access: str | None
    read_action: str | None = None
    write_effect: str | None = None
    fields: tuple = ()
    constraint: bool = False

def properties(node, parent):
    d = dict(parent)
    for key in ('size', 'access', 'readAction', 'modifiedWriteValues'):
        value = node.findtext(key)
        if value is not None:
            d[key] = num(value) if key == 'size' else value
    if d.get('access') not in ACCESS | {None}:
        raise SvdError('invalid_access')
    if d.get('readAction') not in READ | {None}:
        raise SvdError('invalid_readAction')
    if d.get('modifiedWriteValues') not in WRITE | {None}:
        raise SvdError('invalid_writeEffect')
    if node.find('writeConstraint') is not None:
        d['constraint'] = True
    return d
NAMED = {'peripheral', 'cluster', 'register', 'field'}
COLLECTIONS = {'peripherals', 'registers', 'fields'}

def num(s):
    if s is None:
        raise SvdError('missing_number')
    s = s.strip()
    if s.startswith('#'):
        s = '0b' + s[1:]
    try:
        return int(s, 16) if s.lower().startswith('0x') else int(s, 2) if s.lower().startswith('0b') else int(s, 10)
    except ValueError:
        raise SvdError('invalid_number:' + s)

def merge(base, own):
    out = clone(base)
    out.attrib.pop('derivedFrom', None)
    forms = ({'bitOffset', 'bitWidth'}, {'lsb', 'msb'}, {'bitRange'})
    own_form = next((group for group in forms if any((own.find(k) is not None for k in group))), None)
    if own_form:
        for old in list(out):
            if old.tag in set().union(*forms) - own_form:
                out.remove(old)
    for child in own:
        key = child.findtext('name')
        matches = [x for x in out if x.tag == child.tag and (key is None or x.findtext('name') == key)]
        if len(matches) > 1:
            if child.tag in {'addressBlock'}:
                for old in matches:
                    out.remove(old)
                matches = []
            else:
                raise SvdError('duplicate_element:' + child.tag)
        if matches:
            prev = matches[0]
            idx = list(out).index(prev)
            out.remove(prev)
            value = merge(prev, child) if child.tag in COLLECTIONS or child.tag in NAMED else clone(child)
            out.insert(idx, value)
        else:
            out.append(clone(child))
    return out

def instances(node, offset_tag):
    name = node.findtext('name')
    offset = num(node.findtext(offset_tag))
    if offset < 0:
        raise SvdError('negative_offset')
    dim = node.findtext('dim')
    if dim is None:
        if node.find('dimIncrement') is not None:
            raise SvdError('increment_without_dim')
        yield (name, offset)
        return
    count = num(dim)
    stride = num(node.findtext('dimIncrement'))
    if not 1 <= count <= 4096 or stride <= 0 or '%s' not in name:
        raise SvdError('invalid_dim')
    raw = node.findtext('dimIndex')
    if raw is None:
        indices = [str(x) for x in range(count)]
    elif ',' in raw:
        indices = [x.strip() for x in raw.split(',')]
    elif re.fullmatch('\\d+-\\d+', raw):
        a, z = map(int, raw.split('-'))
        if z - a + 1 != count:
            raise SvdError('dim_count')
        indices = list(map(str, range(a, z + 1)))
    elif re.fullmatch('[A-Za-z]-[A-Za-z]', raw):
        a, z = raw.split('-')
        indices = [chr(x) for x in range(ord(a), ord(z) + 1)]
    else:
        indices = [raw]
    if len(indices) != count or len(set(indices)) != count:
        raise SvdError('dim_count')
    for i, index in enumerate(indices):
        yield (name.replace('%s', index), offset + i * stride)

class Catalog:

    def __init__(self, xml):
        if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
            raise SvdError('doctype')
        self.sha256 = hashlib.sha256(xml.encode()).hexdigest()
        self.registers = {}
        self.metadata = {}
        root = ET.fromstring(xml)
        if root.tag != 'device' or root.findtext('addressUnitBits') != '8':
            raise SvdError('device_address_units')
        for node in root.iter():
            if node.tag in {'protection', 'alternateGroup'}:
                raise SvdError('unsupported_' + node.tag)
        index = {}
        resolved = {}
        active = set()

        def scan(node, path):
            for child in node:
                cp = path
                if child.tag in NAMED:
                    name = child.findtext('name')
                    if not name:
                        raise SvdError('missing_name')
                    cp = path + (name,)
                    if cp in index:
                        raise SvdError('duplicate_name')
                    index[cp] = child
                scan(child, cp)
        scan(root, ())
        prop_active = set()

        def scope_props(path):
            if not path:
                return {k: root.findtext(k) for k in ('size', 'access') if root.findtext(k) is not None}
            if path in prop_active:
                raise SvdError('derived_cycle')
            if len(prop_active) >= BUDGET.get().limits.derived_depth:
                raise SvdError('limit_derived_depth')
            prop_active.add(path)
            n = index[path]
            props = scope_props(path[:-1])
            ref = n.get('derivedFrom')
            if ref:
                bp = tuple(ref.split('.')) if '.' in ref else path[:-1] + (ref,)
                if bp not in index:
                    raise SvdError('missing_derived:' + ref)
                props.update(scope_props(bp))
            for k in ('size', 'access'):
                if n.findtext(k) is not None:
                    props[k] = n.findtext(k)
            prop_active.remove(path)
            return props

        def get(path):
            if path in active:
                raise SvdError('derived_cycle')
            if path in resolved:
                return clone(resolved[path])
            if path not in index:
                raise SvdError('missing_derived:' + '.'.join(path))
            if len(active) >= BUDGET.get().limits.derived_depth:
                raise SvdError('limit_derived_depth')
            active.add(path)
            node = index[path]
            base = node.get('derivedFrom')
            if base:
                bp = tuple(base.split('.')) if '.' in base else path[:-1] + (base,)
                other = get(bp)
                if other.tag != node.tag:
                    raise SvdError('derived_kind')
                node = merge(other, node)
            else:
                node = clone(node)
            for key, value in scope_props(path).items():
                if node.find(key) is None:
                    ET.SubElement(node, key).text = value

            def children(el, scope):
                for n in list(el):
                    if n.tag in NAMED:
                        np = scope + (n.findtext('name'),)
                        if np in index:
                            replacement = get(np)
                            if not index[np].get('derivedFrom'):
                                for key in ('size', 'access'):
                                    if index[np].find(key) is None and n.find(key) is not None:
                                        for generated in list(replacement):
                                            if generated.tag == key:
                                                replacement.remove(generated)
                            el[list(el).index(n)] = merge(n, replacement)
                    elif n.tag in COLLECTIONS:
                        children(n, scope)
            children(node, path)
            active.remove(path)
            resolved[path] = clone(node)
            return node

        def defaults(node, parent):
            d = dict(parent)
            for k in ('size', 'access'):
                if node.findtext(k) is not None:
                    d[k] = num(node.findtext(k)) if k == 'size' else node.findtext(k)
            return d

        def bitpos(f):
            if f.findtext('bitOffset') is not None:
                return (num(f.findtext('bitOffset')), num(f.findtext('bitWidth')))
            if f.findtext('lsb') is not None:
                lo = num(f.findtext('lsb'))
                return (lo, num(f.findtext('msb')) - lo + 1)
            match = re.fullmatch('\\[(\\d+):(\\d+)\\]', f.findtext('bitRange') or '')
            if not match:
                raise SvdError('field_position')
            hi, lo = map(int, match.groups())
            return (lo, hi - lo + 1)

        def visit(node, prefix, base, parent):
            offset_tag = 'baseAddress' if node.tag == 'peripheral' else 'addressOffset'
            for name, offset in instances(node, offset_tag):
                BUDGET.get().consume('instances', 1)
                full = prefix + (name,)
                address = base + offset
                d = defaults(node, parent)
                if node.tag != 'register':
                    container = node.find('registers') if node.tag == 'peripheral' else node
                    if container is not None:
                        for child in container:
                            if child.tag in ('register', 'cluster'):
                                visit(child, full, address, d)
                    continue
                d = properties(node, d)
                width = d.get('size')
                if width not in (8, 16, 32):
                    raise SvdError('width')
                if address % (width // 8) or not 0 <= address <= 2 ** 32 - width // 8:
                    raise SvdError('address')
                fields = []
                mask = 0
                names = set()
                for f in node.findall('./fields/field'):
                    fd = properties(f, d)
                    lo, size = bitpos(f)
                    fcopy = clone(f)
                    for old in list(fcopy):
                        if old.tag == 'bitOffset':
                            fcopy.remove(old)
                    ET.SubElement(fcopy, 'bitOffset').text = str(lo)
                    for fname, pos in instances(fcopy, 'bitOffset'):
                        BUDGET.get().consume('instances', 1)
                        if size <= 0 or pos + size > width:
                            raise SvdError('field_range')
                        fm = (1 << size) - 1 << pos
                        if mask & fm or fname in names:
                            raise SvdError('overlapping_fields')
                        mask |= fm
                        names.add(fname)
                        fields.append((fname, pos, size, fd.get('access'), fd.get('readAction'), fd.get('modifiedWriteValues'), fd.get('constraint', False)))
                path = '.'.join(full)
                if path in self.registers:
                    raise SvdError('expanded_name_collision')
                BUDGET.get().consume('registers', 1)
                self.registers[path] = Register(path, address, width, d.get('access'), d.get('readAction'), d.get('modifiedWriteValues'), tuple(fields), d.get('constraint', False))
                self.metadata[path] = {'alternateRegister': node.findtext('alternateRegister')}
        parent = defaults(root, {})
        for peripheral in root.findall('./peripherals/peripheral'):
            visit(get((peripheral.findtext('name'),)), (), 0, parent)
props = 'size access resetValue resetMask'
dim = 'dim dimIncrement dimIndex dimName'
named = 'name description'
policy = 'readAction modifiedWriteValues writeConstraint'
allowed = {
    'device': f'{named} vendor vendorID series version licenseText cpu headerSystemFilename headerDefinitionsPrefix addressUnitBits width {props} peripherals',
    'cpu': 'name revision endian mpuPresent fpuPresent fpuDP dspPresent icachePresent dcachePresent itcmPresent dtcmPresent vtorPresent nvicPrioBits vendorSystickConfig deviceNumInterrupts sauNumRegions',
    'peripherals': 'peripheral',
    'peripheral': f'{named} version groupName prependToName appendToName headerStructName baseAddress {props} {dim} addressBlock interrupt registers',
    'registers': 'register cluster',
    'cluster': f'{named} headerStructName addressOffset {props} {dim} register cluster',
    'register': f'{named} displayName alternateRegister addressOffset {props} {dim} {policy} fields',
    'fields': 'field',
    'field': f'{named} bitOffset bitWidth lsb msb bitRange access {dim} {policy} enumeratedValues',
    'enumeratedValues': 'name headerEnumName usage enumeratedValue',
    'enumeratedValue': f'{named} value isDefault',
    'writeConstraint': 'writeAsRead useEnumeratedValues range',
    'range': 'minimum maximum',
    'addressBlock': 'offset size usage',
    'interrupt': f'{named} value',
}
allowed = {k: set(v.split()) for k, v in allowed.items()}
repeat = {
    'peripherals': {'peripheral'},
    'registers': {'register', 'cluster'},
    'cluster': {'register', 'cluster'},
    'peripheral': {'addressBlock', 'interrupt'},
    'fields': {'field'},
    'field': {'enumeratedValues'},
    'enumeratedValues': {'enumeratedValue'},
}

class StrictCatalog(Catalog):

    def __init__(self, xml):
        if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
            raise SvdError('doctype')
        root = ET.fromstring(xml)
        if root.findtext('./cpu/endian') not in (None, 'little'):
            raise SvdError('unsupported_endian')
        for node in root.iter():
            attrs = {'derivedFrom'} if node.tag in {'peripheral', 'cluster', 'register', 'field'} else set()
            if node is root:
                attrs = {'schemaVersion', '{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation'}
            if set(node.attrib) - attrs:
                raise SvdError('unsupported_attribute:' + node.tag)
            seen = set()
            for child in node:
                if child.tag not in allowed.get(node.tag, set()):
                    raise SvdError('unsupported_element:' + node.tag + '/' + child.tag)
                if child.tag in seen and child.tag not in repeat.get(node.tag, set()):
                    raise SvdError('duplicate_element:' + child.tag)
                seen.add(child.tag)
            if node.tag == 'field':
                forms = [{'bitOffset', 'bitWidth'}, {'lsb', 'msb'}, {'bitRange'}]
                if sum((bool(seen & f) for f in forms)) > 1:
                    raise SvdError('ambiguous_field_position')
            if node.find('dim') is None and seen & {'dimIncrement', 'dimIndex', 'dimName'}:
                raise SvdError('dimension_without_dim')
            if node.find('dim') is not None:
                name = node.findtext('name') or ''
                if name.count('%s') != 1:
                    raise SvdError('invalid_dim_name')
                indices = node.findtext('dimIndex')
                if indices is not None and any((not x.strip() for x in indices.split(','))):
                    raise SvdError('empty_dim_index')
        super().__init__(xml)

@dataclass(frozen=True)
class Limits:
    bytes: int = 8 * 1024 * 1024
    depth: int = 64
    nodes: int = 100000
    derived_depth: int = 32
    instances: int = 100000
    registers: int = 100000
    copies: int = 2000000

    def __post_init__(self):
        for key, value in asdict(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError('invalid_limit:' + key)

class Budget:

    def __init__(self, limits):
        self.limits = limits
        self.used = {}

    def consume(self, key, n):
        value = self.used.get(key, 0) + n
        if value > getattr(self.limits, key):
            raise ValueError('limit_' + key)
        self.used[key] = value

@dataclass(frozen=True)
class Snapshot:
    sha256: str
    registers: object
    metadata: object

def _parse(raw, limits):
    if len(raw) > limits.bytes:
        raise ValueError('limit_bytes')
    text = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('doctype')
    parser = ET.XMLPullParser(events=('start', 'end'))
    depth = 0
    nodes = 0
    for offset in range(0, len(text), 1024):
        parser.feed(text[offset:offset + 1024])
        for kind, node in parser.read_events():
            if kind == 'start':
                depth += 1
                nodes += 1
                if depth > limits.depth:
                    raise ValueError('limit_depth')
                if nodes > limits.nodes:
                    raise ValueError('limit_nodes')
            else:
                depth -= 1
    parser.close()
    budget = Budget(limits)
    token = BUDGET.set(budget)
    try:
        catalog = StrictCatalog(text)
    finally:
        BUDGET.reset(token)
    return Snapshot(hashlib.sha256(raw).hexdigest(), MappingProxyType(dict(catalog.registers)), MappingProxyType({k: MappingProxyType(dict(v)) for k, v in catalog.metadata.items()}))

def parse(raw, limits=Limits()):
    """Parse immutable bytes, returning an immutable catalog or a stable diagnostic."""
    try:
        return _parse(raw, limits)
    except (ET.ParseError, UnicodeError) as exc:
        raise SvdError('svd.syntax') from exc
    except (ValueError, TypeError, RecursionError) as exc:
        detail = str(exc)
        if detail.startswith('limit_'):
            code = 'svd.limit'
        elif 'derived' in detail or 'duplicate_name' in detail or 'collision' in detail:
            code = 'svd.reference'
        elif 'doctype' in detail or 'unsupported' in detail:
            code = 'svd.forbidden_construct'
        else:
            code = 'svd.syntax'
        raise SvdError(code, detail) from exc

def read_source(path):
    """Bound file allocation before parsing; no implicit environment expansion."""
    try:
        with path.open('rb') as stream:
            raw = stream.read(Limits().bytes + 1)
    except OSError as exc:
        raise SvdError('svd.source') from exc
    if len(raw) > Limits().bytes:
        raise SvdError('svd.limit', 'limit_bytes')
    return raw


def save_source(directory, snapshot, raw):
    """Save and verify source bytes before any server can start."""
    if hashlib.sha256(raw).hexdigest() != snapshot.sha256:
        raise SvdError('svd.integrity')
    path = directory / 'source.svd'
    try:
        path.write_bytes(raw)
        if path.read_bytes() != raw:
            raise SvdError('svd.integrity')
    except OSError as exc:
        raise SvdError('svd.capture') from exc
    return dict(sha256=snapshot.sha256, path='source.svd', registers=len(snapshot.registers))
