"""Verify the package and its source hashes before any connection."""
import hashlib
import json
from pathlib import Path

def validate(directory):
    d = Path(directory)
    m = json.loads((d / 'manifest.json').read_text())
    for group, root in (('files', d), ('sources', Path(__file__).resolve().parent)):
        for name, digest in m[group].items():
            if Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('nonlocal manifest path')
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
                raise ValueError('package changed: ' + name)
    if m['displaced'] != '80b483b0' or m['vectors'] != 512 or m['sector'] != 16384:
        raise ValueError('unqualified layout')
    return m
