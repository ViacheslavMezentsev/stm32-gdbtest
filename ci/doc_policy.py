"""Required bilingual entry points and complete API reference; optional docs may be RU-only."""
import os
from pathlib import Path

ROOT_PAIRS = (("README.md", "README.en.md"), ("CHANGELOG.md", "CHANGELOG.en.md"))
LOCALIZED = ("index.md", "DDTT.md", "API.md")


def check(root):
    root = Path(root)
    errors = []
    for pair in ROOT_PAIRS:
        errors.extend(name for name in pair if not (root / name).is_file())
    ru, en = root / "docs/ru", root / "docs/en"
    required = set(LOCALIZED)
    for base in (ru, en):
        required.update(p.relative_to(base).as_posix() for p in (base / "api").rglob("*.md"))
    required.add("api/index.md")
    for name in sorted(required):
        for base, other in ((ru, en), (en, ru)):
            page = base / name
            if not page.is_file():
                errors.append(page.relative_to(root).as_posix())
                continue
            header = "\n".join(page.read_text(encoding="utf-8").splitlines()[:4])
            link = Path(os.path.relpath(other / name, page.parent)).as_posix()
            if f"({link})" not in header or (page.name != "index.md" and "(index.md)" not in header):
                errors.append("navigation in " + page.relative_to(root).as_posix())
    if errors:
        raise ValueError("Required RU/EN documentation: " + ", ".join(errors))
