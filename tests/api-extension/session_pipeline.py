"""Research-only preparation/package/facade pipeline; no hardware execution."""

import json
from pathlib import Path
import shutil
import tempfile

from config_transport import dumps, loads
from session_bridge import prepare
from stm32_gdbtest.build_manifest import digest, load_verified
from stm32_gdbtest.package import open_package, pack
from stm32_gdbtest.runner import run


HERE = Path(__file__).resolve().parent


class ConfiguredTarget:
    """Research facade; public read properties cannot be reassigned."""

    def __init__(self, target, snapshot):
        self._target = target
        self._snapshot = snapshot

    @property
    def config(self):
        return self._snapshot.config

    @property
    def config_props(self):
        return self._snapshot.config_props

    def __getattr__(self, name):
        return getattr(self._target, name)


def prepare_and_pack(session, output, test_ids, *, preflight=None):
    """Freeze inputs before real prepare; package using unchanged production code.

    preflight is injectable only for host tests; default is real runner prepare-only.
    The resulting ordinary schema-1 archive needs open_configured to attach its
    research capsule. Plain production --package does not install this facade.
    """
    _, capsule = prepare(session)
    if capsule is None:
        raise ValueError("research pipeline requires session_config")
    snapshot = loads(capsule)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="config-stage-", dir=output.parent) as directory:
        root = Path(directory)
        profile = root / "profile"
        profile.mkdir()
        (profile / "target.toml").write_bytes(snapshot._source_bytes["target"])
        shutil.copytree(Path(session["tests"]).parent, profile / "tests",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (root / "firmware.elf").write_bytes(Path(session["elf"]).read_bytes())
        (root / "build-manifest.json").write_bytes(Path(session["build_manifest"]).read_bytes())
        load_verified(root / "build-manifest.json", digest(root / "firmware.elf"), profile / "target.toml")
        helper = root / "research"
        helper.mkdir()
        (helper / "config.json").write_text(capsule, encoding="utf-8")
        # Keep the original source bytes in the capsule; this is merely the
        # policy adapter for the existing runner, which accepts a file path.
        image = None
        if "image" in snapshot._source_bytes:
            image = helper / "image.toml"
            image.write_bytes(snapshot._source_bytes["image"])
        frozen = dict(session, root=str(root), elf=str(root / "firmware.elf"),
                      profile=str(profile / "target.toml"),
                      tests=str(profile / "tests" / Path(session["tests"]).name),
                      build_manifest=str(root / "build-manifest.json"), out=str(root / "runs"))
        frozen.pop("session_config", None)
        outcomes = []

        def check(case):
            if preflight is not None:
                status = preflight(frozen, case, image)
            else:
                try:
                    status = "PASS" if run(frozen, case, image_policy=image, prepare_only=True) == 0 else "ERROR"
                finally:
                    for report_dir in (root / "runs").glob("*"):
                        destination = output.parent / "prepare" / report_dir.name
                        if not destination.exists():
                            shutil.copytree(report_dir, destination)
            outcomes.append(dict(id=case["id"], status=status))
            return status

        manifest = pack(frozen, output, test_ids=test_ids, include=["research"], prepare=check)
    return dict(prepared=outcomes, elf_sha256=manifest["elf_sha256"],
                config_sha256=snapshot.session_sha256)


def open_configured(path, workdir, gdb):
    """Verify production package and bind its config to packaged ELF/profile."""
    session = open_package(path, workdir, gdb)
    snapshot = loads((Path(session["root"]) / "research/config.json").read_text(encoding="utf-8"))
    if digest(session["profile"]) != snapshot.config_props["target"]["sha256"]:
        raise ValueError("capsule target differs from packaged profile")
    load_verified(session["build_manifest"], digest(session["elf"]), session["profile"])
    return session, snapshot
