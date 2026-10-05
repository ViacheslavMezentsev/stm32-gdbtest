"""Read-only profile of a scenario run (ТЗ API 4.14).

`Target.profile` keeps the published 0.1 behaviour: indexing returns the keys of `target.toml`
(`profile["flash_start"]`). The sections describe the rest of the run: the effective `api.toml`,
its `[user]` parameters, the image policy, the project data files, the captured files, the build,
the current case, the stand and the GDB in use. Every section is read-only; values are plain
Python types.
"""

from collections.abc import Mapping
import os
from types import MappingProxyType

from stm32_gdbtest.configuration import DEFAULTS, EXECUTE_OUTPUT_LIMIT, FRAMES_LIMIT, freeze

SECTIONS = ("target", "api", "user", "image", "data", "files", "build", "case", "stand", "gdb")

# Effective defaults of `api.toml` keys that the core applies when the file omits them (ТЗ API 6.6).
API_DEFAULTS = MappingProxyType({
    "records": DEFAULTS,
    "frames": MappingProxyType({"limit": FRAMES_LIMIT}),
    "execute": MappingProxyType({"output_limit_chars": EXECUTE_OUTPUT_LIMIT}),
})

_ABSENT = object()


def _lookup(mapping, parts):
    value = mapping
    for part in parts:
        if not isinstance(value, Mapping) or part not in value:
            return _ABSENT
        value = value[part]
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class Profile(Mapping):
    """Profile of the current run; indexing reads `target.toml` as in 0.1/0.2."""

    def __init__(self, target, configuration=None, *, case=None, stand=None, gdb=None, build=None):
        self._target = freeze(dict(target)) if not isinstance(target, MappingProxyType) else target
        config = configuration.config if configuration else None
        props = configuration.config_props if configuration else None
        api = dict(config["api"]) if config and config.get("api") is not None else {"schema": 1}
        merged = {name: (MappingProxyType({**default, **api[name]}) if isinstance(api.get(name), Mapping)
                         else default) for name, default in API_DEFAULTS.items()}
        self._api = freeze({**api, **{k: dict(v) for k, v in merged.items()}})
        self._api_file = props["api"]["data"] if props and props.get("api") else None
        image = config.get("image") if config else None
        self._image = image["image"] if isinstance(image, Mapping) and "image" in image else image
        self._data = config.get("data") if config and config.get("data") is not None else MappingProxyType({})
        files = {}
        for role in ("target", "api", "image", *sorted(name for name in (props or {}) if name.startswith("data."))):
            entry = props.get(role) if props else None
            if entry is not None:
                files[role] = {"reference": entry["reference"], "sha256": entry["sha256"]}
        if configuration is not None and configuration.session_sha256:
            files["session"] = {"reference": "session.toml", "sha256": configuration.session_sha256}
        self._files = freeze(files)
        # Without a build manifest the section is None: nothing is known about the build.
        self._build = freeze(dict(build)) if build is not None else None
        self._case = freeze(dict(case or {}))
        self._stand = freeze(dict(stand or {}))
        # The GDB section is a live read-only view: the stop details become known at the first stop.
        self._gdb_state = dict(gdb or {})
        self._gdb = MappingProxyType(self._gdb_state)

    # Mapping over target.toml, the published 0.1 contract of Target.profile.
    def __getitem__(self, key):
        return self._target[key]

    def __iter__(self):
        return iter(self._target)

    def __len__(self):
        return len(self._target)

    def __repr__(self):
        return f"Profile(mcu={self._target.get('mcu')!r}, case={self._case.get('id')!r})"

    @property
    def target(self):
        return self._target

    @property
    def api(self):
        return self._api

    @property
    def user(self):
        return self._api.get("user", MappingProxyType({}))

    @property
    def image(self):
        return self._image

    @property
    def data(self):
        """Project data files declared in `[data]` of session.toml, by name (`data["board"]`)."""
        return self._data

    @property
    def build(self):
        """Summary of the build manifest: compilers, Cube packages, library versions, defines; or None."""
        return self._build

    @property
    def files(self):
        return self._files

    @property
    def case(self):
        return self._case

    @property
    def stand(self):
        return self._stand

    @property
    def gdb(self):
        return self._gdb

    def _section(self, name):
        return getattr(self, name)

    def get(self, path, default=None):
        """Value by a dotted path; a path without a known section reads `target.toml`."""
        if type(path) is not str or not path:
            return default
        parts = path.split(".")
        if parts[0] in SECTIONS:
            value = _lookup(self._section(parts[0]), parts[1:]) if len(parts) > 1 else self._section(parts[0])
        else:
            value = _lookup(self._target, parts)
        return default if value is _ABSENT else value

    def origin(self, path):
        """Where the value of a dotted path comes from: a file, a core default, an override or the run."""
        parts = path.split(".") if type(path) is str and path else []
        if not parts:
            raise KeyError(path)
        section = parts[0] if parts[0] in SECTIONS else "target"
        keys = parts[1:] if parts[0] in SECTIONS else parts
        if section == "user":
            section, keys = "api", ["user", *keys]
        if self.get(".".join([section, *keys]) if keys else section, _ABSENT) is _ABSENT:
            raise KeyError(path)
        if section in ("case", "stand", "gdb", "build"):
            return MappingProxyType({"state": "run", "section": section})
        if section == "data":
            if not keys:
                return MappingProxyType({"state": "run", "section": section})
            entry = self._files["data." + keys[0]]
            return MappingProxyType({"state": "file", "file": entry["reference"], "sha256": entry["sha256"]})
        if section == "api" and keys[:2] == ["reset", "command"] and os.environ.get("STM32_GDBTEST_RESET_COMMAND"):
            return MappingProxyType({"state": "override", "variable": "STM32_GDBTEST_RESET_COMMAND"})
        if section == "api" and (self._api_file is None or _lookup(self._api_file, keys) is _ABSENT):
            return MappingProxyType({"state": "default"})
        entry = self._files.get(section)
        if entry is None:
            return MappingProxyType({"state": "default"})
        return MappingProxyType({"state": "file", "file": entry["reference"], "sha256": entry["sha256"]})

    def snapshot(self):
        """Plain JSON-compatible copy of every section for `record` and reports (ТЗ API 4.14.5)."""
        return {name: _plain(self._section(name)) for name in SECTIONS if name != "user"}

    # Internal: Target refines what the GDB in use reports.
    def _observe_gdb(self, **facts):
        self._gdb_state.update(facts)
