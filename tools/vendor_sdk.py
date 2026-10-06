"""Install a vendor SDK pinned in ci/dependencies.lock.json on this computer, as the CI image does.

The archive is downloaded from the pinned URL (or taken from --archive), checked against the pinned SHA-256 and
only the listed members are extracted. The default destination is the one the CI firmware CMake looks for:
%USERPROFILE%/Artery/<package> on Windows, /opt/Artery/<package> elsewhere (AT32_SDK_ROOT overrides it).
Usage: python tools/vendor_sdk.py [--archive file.zip] [--destination DIR] [name]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "ci/dependencies.lock.json"
DEFAULT_NAME = "at32f403a-407-firmware-library-2.0.9"


def default_destination(item):
    package = Path(item["destination"]).name
    if os.name == "nt":
        return Path(os.environ["USERPROFILE"]) / "Artery" / package
    return Path(item["destination"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", nargs="?", default=DEFAULT_NAME, help="archive name in the lockfile")
    parser.add_argument("--archive", type=Path, help="already downloaded archive instead of the pinned URL")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    items = {item["name"]: item for item in json.loads(LOCK.read_text(encoding="utf-8"))["archives"]}
    if args.name not in items or items[args.name]["kind"] != "zip":
        sys.exit(f"Unknown vendor SDK {args.name}; ZIP archives in the lockfile: "
                 + ", ".join(name for name, item in items.items() if item["kind"] == "zip"))
    item = items[args.name]
    destination = (args.destination or default_destination(item)).resolve()

    with tempfile.TemporaryDirectory() as temp:
        archive = args.archive
        if archive is None:
            archive = Path(temp) / "download.zip"
            print(f"Downloading {item['url']}")
            with urllib.request.urlopen(item["url"], timeout=60) as response, archive.open("wb") as stream:
                shutil.copyfileobj(response, stream)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            sys.exit(f"SHA-256 mismatch: {digest}, the lockfile pins {item['sha256']}")
        with zipfile.ZipFile(archive) as package:
            include = tuple(item.get("include", ()))
            members = [name for name in package.namelist() if not include or name.startswith(include)]
            if any(not (destination / name).resolve().is_relative_to(destination) for name in members):
                sys.exit("Archive member outside the destination")
            package.extractall(destination, members)

    missing = [name for name in item.get("required_files", []) if not (destination / name).is_file()]
    if missing:
        sys.exit("Missing after extraction: " + ", ".join(missing))
    print(f"{len(members)} files in {destination}")
    print(f"AT32_SDK_ROOT={destination}" if "at32" in args.name else destination)


if __name__ == "__main__":
    main()
