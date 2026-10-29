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
    errors.extend(check_reachable(root))
    if errors:
        raise ValueError("Required RU/EN documentation: " + ", ".join(errors))


LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
POINTER_TITLE = ("документ перенесён", "document moved")


def is_pointer(page):
    """A short page left at an old address: its title ends with the agreed marker."""
    lines = page.read_text(encoding="utf-8").splitlines()
    return bool(lines) and lines[0].lower().rstrip(". ").endswith(POINTER_TITLE)


def check_reachable(root):
    """Every page of docs/ru and docs/en is linked from the map: top-level pages directly, nested ones transitively."""
    errors = []
    for lang in ("ru", "en"):
        base = root / "docs" / lang
        index = base / "index.md"
        if not index.is_file():
            continue
        pages = {p.resolve() for p in base.rglob("*.md")} - {index.resolve()}
        direct = {(base / m).resolve() for m in LINK.findall(index.read_text(encoding="utf-8"))}
        seen, queue = set(direct), [p for p in direct if p.is_file()]
        while queue:
            page = queue.pop()
            for target in LINK.findall(page.read_text(encoding="utf-8")):
                path = (page.parent / target).resolve()
                if path in pages and path not in seen:
                    seen.add(path)
                    queue.append(path)
        for page in sorted(pages):
            name = page.relative_to(base.resolve()).as_posix()
            if is_pointer(page):
                continue
            if "/" not in name and page not in direct:
                errors.append(f"docs/{lang}/{name} not linked from index.md")
            elif page not in seen:
                errors.append(f"docs/{lang}/{name} not reachable from index.md")
    return errors


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
