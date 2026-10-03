"""Research read views for an already selected legacy JSON/package session."""
import hashlib
import os
from pathlib import Path
import tomllib
from types import MappingProxyType

from session_config import Configuration, ConfigError, DEFAULTS, freeze, _target_from_snapshot
from stm32_gdbtest.full_image import validate_policy


def load_legacy(session, *, image_policy=None, environ=None, reader=None):
    """Capture legacy sources without inventing session.toml or API input.

    Paths retain current runner semantics (relative to cwd, not the JSON file).
    A packaged policy must be explicitly selected by its extracted path, as in
    the existing CLI; mere inclusion in an archive does not select it.
    This captures views only, not production runner/agent integration.
    """
    if 'session_config' in session:
        raise ConfigError('mode', 'use the explicit session.toml loader')
    environ = os.environ if environ is None else environ
    reader = Path.read_bytes if reader is None else reader
    # Same precedence as runner.run; image_policy_path is a derived internal field.
    selected_image = image_policy or environ.get('STM32_GDBTEST_IMAGE_POLICY')
    refs = {'target': session['profile'], 'image': selected_image}
    cache, raw_sources, props, documents = {}, {}, {'api': None}, {}
    for name, reference in refs.items():
        if not reference:
            props[name] = documents[name] = None
            continue
        source = Path(reference).resolve()
        if source not in cache:
            try:
                raw = reader(source)
                parsed = tomllib.loads(raw.decode('utf-8'))
            except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
                raise ConfigError('source', name) from exc
            cache[source] = (raw, parsed)
        raw, parsed = cache[source]
        raw_sources[name] = raw
        documents[name] = parsed
        props[name] = dict(data=parsed, sha256=hashlib.sha256(raw).hexdigest(),
                           reference=str(reference))
    try:
        target = _target_from_snapshot(raw_sources['target'])
    except ValueError as exc:
        raise ConfigError('target', 'invalid captured target') from exc
    image = documents['image']
    if image is not None:
        try:
            if set(image) != {'image'}:
                raise ValueError('expected [image] only')
            validate_policy(image['image'], target)
        except ValueError as exc:
            raise ConfigError('image', 'invalid captured image') from exc
    effective = dict(target=target, image=image,
                     api=dict(schema=1, records=dict(DEFAULTS)))
    return Configuration(freeze(effective), freeze(props), None,
                         MappingProxyType(raw_sources))
