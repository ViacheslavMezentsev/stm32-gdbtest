"""Immutable scenario configuration captured before MCU access (ТЗ 5.20)."""

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import tomllib
from types import MappingProxyType

from stm32_gdbtest.full_image import validate_policy
from stm32_gdbtest.profile import validate_profile


# Accepted configuration bounds (API specification 0.2.1).
DEFAULTS = MappingProxyType(dict(max_records=128, max_nodes=4096, max_text_bytes=65536,
                                max_depth=8, max_integer_bits=256))
# Output limit of the `execute` journal (ТЗ API 6.6, Q5).
EXECUTE_OUTPUT_LIMIT = 2048
# Default reset command when neither `api.toml` nor the backend names one
# (ТЗ API 6.6, Q2); OpenOCD profiles keep their own `reset_halt` value.
RESET_COMMAND = "monitor reset"
# Default frame limit of `frames` (ТЗ API 6.6, Q1); `api.toml` may lower or raise it.
FRAMES_LIMIT = 16

# Largest block that `memory`/`write_memory` move in one call (ТЗ API 6.8).
MEMORY_LIMIT = 4096
MAXIMUMS = MappingProxyType(dict(max_records=1024, max_nodes=32768,
                                max_text_bytes=524288, max_depth=32,
                                max_integer_bits=1024))


class ConfigError(ValueError):
    """Internal configuration diagnostic; not a scenario API exception."""

    def __init__(self, code, detail):
        self.code = code
        super().__init__(f"{code}: {detail}")


def freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(freeze(v) for v in value)
    return value  # TOML scalars, including date/time, are immutable.


@dataclass(frozen=True)
class Configuration:
    config: object
    config_props: object
    session_sha256: str | None
    _source_bytes: object = field(repr=False)


def _target_from_snapshot(raw):
    return validate_profile(tomllib.loads(raw.decode("utf-8")))


def load_session(path, *, profile=None, image_policy=None, environ=None,
                 reader=None):
    """Capture selected TOML files once, validate, and build detached read views.

    Known record limits are exact integers in the accepted inclusive ranges.
    Unknown API fields remain available to the scenario without interpretation.
    """
    environ = os.environ if environ is None else environ
    if profile is not None or image_policy is not None or environ.get(
            "STM32_GDBTEST_IMAGE_POLICY"):
        raise ConfigError("conflict", "session config and PROFILE/image override")
    path = Path(path).resolve()
    reader = Path.read_bytes if reader is None else reader
    cache = {}

    def capture(source):
        source = source.resolve()
        if source not in cache:
            try:
                raw = reader(source)
                data = tomllib.loads(raw.decode("utf-8"))
            except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
                raise ConfigError("source", str(source)) from exc
            cache[source] = (raw, data, hashlib.sha256(raw).hexdigest())
        return cache[source]

    session_raw, session, session_sha = capture(path)
    if set(session) != {"config"} or type(session["config"]) is not dict:
        raise ConfigError("session", "expected [config]")
    links = session["config"]
    if "target" not in links or set(links) - {"target", "api", "image"}:
        raise ConfigError("session", "target required; known file links only")
    documents, props, raw_documents = {}, {}, {}
    for name in ("target", "api", "image"):
        if name not in links:
            documents[name] = props[name] = None
            continue
        reference = links[name]
        if type(reference) is not str or not reference.strip():
            raise ConfigError("reference", name)
        raw, data, sha = capture(path.parent / reference)
        documents[name] = data
        raw_documents[name] = raw
        props[name] = dict(data=data, sha256=sha, reference=reference)

    try:
        target = _target_from_snapshot(raw_documents["target"])
    except ValueError as exc:
        raise ConfigError("target", "invalid target configuration") from exc
    image = documents["image"]
    if image is not None:
        try:
            if set(image) != {"image"}:
                raise ValueError("expected [image]")
            validate_policy(image["image"], target)
        except ValueError as exc:
            raise ConfigError("image", "invalid image configuration") from exc

    api = documents["api"]
    if api is None:
        api = {"schema": 1}
    if type(api.get("schema")) is not int or api["schema"] != 1:
        raise ConfigError("api_schema", "expected integer schema=1")
    records = api.get("records", {})
    if type(records) is not dict:
        raise ConfigError("api_parameter", "records must be a table")
    for name in DEFAULTS:
        if name in records and (type(records[name]) is not int or
                                not 1 <= records[name] <= MAXIMUMS[name]):
            raise ConfigError("api_parameter", f"records.{name}: expected integer 1..{MAXIMUMS[name]}")
    effective_api = dict(api, records={**DEFAULTS, **records})
    effective = dict(target=target, api=effective_api, image=image)
    return Configuration(freeze(effective), freeze(props), session_sha,
                         MappingProxyType(dict(raw_documents, session=session_raw)))


def load_legacy(session, *, image_policy=None, environ=None, reader=None):
    """Capture legacy sources without inventing session.toml or API input.

    Paths retain current runner semantics (relative to cwd, not the JSON file).
    A packaged policy must be explicitly selected by its extracted path, as in
    the existing CLI; mere inclusion in an archive does not select it.
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


def thaw(value):
    """Convert immutable views to detached JSON-compatible profile containers."""
    if isinstance(value, MappingProxyType):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


def select_target(path):
    snapshot = load_session(path)
    return (Path(path).resolve().parent / snapshot.config_props["target"]["reference"]).resolve()


def capture(session, *, image_policy=None, environ=None):
    """Resolve legacy or explicit configuration once; reject stale selection."""
    environ = os.environ if environ is None else environ
    if "_config_capsule" in session:
        from stm32_gdbtest.config_transport import loads
        if image_policy or environ.get("STM32_GDBTEST_IMAGE_POLICY"):
            raise ConfigError("conflict", "captured configuration and image override")
        return loads(session["_config_capsule"])
    if "session_config" not in session:
        return load_legacy(session, image_policy=image_policy, environ=environ)
    path = Path(session["session_config"])
    snapshot = load_session(path, image_policy=image_policy, environ=environ)
    selected = (path.resolve().parent / snapshot.config_props["target"]["reference"]).resolve()
    if Path(session["profile"]).resolve() != selected:
        raise ConfigError("stale_selection", "regenerate session after changing target selection")
    return snapshot


if __name__ == "__main__":
    import sys
    print(select_target(sys.argv[1]).as_posix())
