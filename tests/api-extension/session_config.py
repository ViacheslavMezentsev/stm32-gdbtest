"""Research-only host loader. No CLI, GDB, firmware or runner integration."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
import tomllib
from types import MappingProxyType

from stm32_gdbtest.full_image import validate_policy
from stm32_gdbtest.profile import load_profile


# Experimental defaults, not an approved resource budget.
DEFAULTS = MappingProxyType(dict(max_records=128, max_nodes=4096, max_text_bytes=65536,
                                max_depth=8, max_integer_bits=256))


class ConfigError(ValueError):
    """Prototype diagnostic; codes are not yet a public API contract."""

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
    session_sha256: str


def _target_from_snapshot(raw):
    # Reuse the existing complete validator without rereading the source path or
    # changing production code. The temporary file holds captured bytes only.
    # Integration should extract a pure validator instead of retaining this shim.
    with tempfile.TemporaryDirectory(prefix="gdbtest-config-") as directory:
        path = Path(directory) / "target.toml"
        path.write_bytes(raw)
        return load_profile(path)


def load_session(path, *, profile=None, image_policy=None, environ=None,
                 reader=None):
    """Capture selected TOML files once, validate, and build detached read views.

    Positive limit validation is experimental; upper bounds await Q6/Q19.
    This function supports only the new mode. Legacy/CMake/package work is M4.
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

    _, session, session_sha = capture(path)
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
        if name in records and (type(records[name]) is not int or records[name] <= 0):
            raise ConfigError("api_parameter", "records." + name)
    effective_api = dict(api, records={**DEFAULTS, **records})
    effective = dict(target=target, api=effective_api, image=image)
    return Configuration(freeze(effective), freeze(props), session_sha)
