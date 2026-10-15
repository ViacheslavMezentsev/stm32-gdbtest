"""Bind a reviewed template to current source bytes and a built ELF; no board access."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("project", "elf", "template", "out"):
        parser.add_argument("--" + key, required=True)
    args = parser.parse_args()
    root = Path(args.project).resolve()
    data = json.loads(Path(args.template).read_text(encoding="utf-8"))
    data["elf_sha256"] = hashlib.sha256(Path(args.elf).read_bytes()).hexdigest()
    for point in data["points"]:
        path = (root / point["source"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("source outside project")
        if sum(line.strip() == point["anchor"].strip() for line in path.read_text(encoding="utf-8-sig").splitlines()) != 1:
            raise ValueError("Review changed/ambiguous anchor: " + point["anchor"])
        point["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
