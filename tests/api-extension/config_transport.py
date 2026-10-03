"""Experimental config capsule; source TOML bytes avoid lossy JSON type mapping."""

import base64
import hashlib
import json
from pathlib import Path
import zipfile

from session_config import ConfigError, DEFAULTS, load_session


def fingerprint():
    return hashlib.sha256(json.dumps(dict(DEFAULTS), sort_keys=True).encode()).hexdigest()


def dumps(snapshot):
    files = {name: {"base64": base64.b64encode(raw).decode("ascii"),
                    "sha256": hashlib.sha256(raw).hexdigest()}
             for name, raw in snapshot._source_bytes.items()}
    return json.dumps(dict(format="research-config", schema=1,
                           defaults=fingerprint(), files=files), allow_nan=False)


def loads(text):
    def unique(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ConfigError("transport", "duplicate JSON key")
            result[k] = v
        return result
    try:
        data = json.loads(text, object_pairs_hook=unique)
        if (set(data) != {"format", "schema", "defaults", "files"}
                or data["format"] != "research-config" or type(data["schema"]) is not int
                or data["schema"] != 1 or data["defaults"] != fingerprint()):
            raise ValueError("incompatible capsule or defaults")
        files = data["files"]
        if not {"session", "target"} <= set(files) or set(files) - {"session", "target", "api", "image"}:
            raise ValueError("invalid capsule file set")
        raw = {}
        for name, item in files.items():
            if set(item) != {"base64", "sha256"}:
                raise ValueError("invalid source metadata")
            value = base64.b64decode(item["base64"], validate=True)
            if hashlib.sha256(value).hexdigest() != item["sha256"]:
                raise ValueError("source hash mismatch")
            raw[name] = value
        import tomllib
        session = tomllib.loads(raw["session"].decode("utf-8"))
        links = session["config"]
        if set(raw) != {"session", *links}:
            raise ValueError("source set differs from session references")
        # This virtual root is never read/written. Even absolute source references
        # are served only from this map, never reopened on the receiving host.
        root = Path("__research_config_virtual__").resolve()
        entry = root / "session.toml"
        sources = {entry: raw["session"]}
        for name, reference in links.items():
            if type(reference) is not str:
                raise ValueError("invalid reference")
            path = (root / reference).resolve()
            if path in sources and sources[path] != raw[name]:
                raise ValueError("conflicting source aliases")
            sources[path] = raw[name]
        return load_session(entry, environ={}, reader=sources.__getitem__)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        raise ConfigError("transport", str(exc)) from exc


def pack_config(snapshot, path):
    """Config-only research archive, not a production ddtt-package."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("config.json", dumps(snapshot))


def open_config(path):
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != ["config.json"]:
            raise ConfigError("transport", "unexpected archive entries")
        return loads(archive.read("config.json").decode("utf-8"))
