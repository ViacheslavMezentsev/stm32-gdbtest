"""Required bilingual entry points and complete API reference; optional docs may be RU-only."""
import os
import re
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
    errors.extend(check_readme(root))
    if errors:
        raise ValueError("Required RU/EN documentation: " + ", ".join(errors))


README_MAX_LINES = 110
BADGE = re.compile(r"img\.shields\.io/(\S+?)\)")
LIVE_BADGES = ("github/actions/workflow/status/", "github/v/release/")


def check_readme(root):
    """README rules from docs/development/README.md: length, matching sections, live badges only."""
    errors, sections = [], []
    for name in ("README.md", "README.en.md"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if len(text.splitlines()) > README_MAX_LINES:
            errors.append(f"{name} longer than {README_MAX_LINES} lines")
        errors.extend(f"{name} badge {badge}" for badge in BADGE.findall(text)
                      if not badge.startswith(LIVE_BADGES))
        sections.append(len(re.findall(r"(?m)^## ", text)))
    if len(sections) == 2 and sections[0] != sections[1]:
        errors.append("README.md and README.en.md differ in sections")
    return errors
