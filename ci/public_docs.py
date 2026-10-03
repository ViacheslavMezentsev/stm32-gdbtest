"""Reject published development material and links into locally ignored research."""
import fnmatch
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit


def private_patterns(root):
    text = (root / '.gitignore').read_text(encoding='utf-8')
    start = '# BEGIN local development materials'
    end = '# END local development materials'
    section = text.split(start, 1)[1].split(end, 1)[0]
    patterns = [line.strip().strip('/') for line in section.splitlines()
                if line.startswith('/')]
    if not patterns:
        raise ValueError('Missing local-development filters in .gitignore')
    return patterns


def is_private(path, patterns):
    path = str(path).replace('\\', '/').strip('/').lower()
    ancestors = ['/'.join(path.split('/')[:i]) for i in range(1, len(path.split('/')) + 1)]
    for pattern in patterns:
        # Git **/ also matches zero directory components.
        variants = {pattern.lower(), pattern.lower().replace('/**/', '/')}
        if any(fnmatch.fnmatchcase(parent, variant) for parent in ancestors for variant in variants):
            return True
    return False


def files(root):
    """Use the index in a checkout, or all shipped files in a Git-free CI snapshot."""
    if (root / '.git').exists():
        result = subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True, capture_output=True)
        return [Path(name) for name in result.stdout.decode('utf-8').split('\0') if name]
    paths = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('build', '.git', '__pycache__')]
        paths.extend((Path(base) / name).relative_to(root) for name in names)
    return paths


def links(text):
    # Inline Markdown, reference definitions, HTML attributes and URL autolinks.
    patterns = [r'\]\(\s*(<[^>]+>|[^\s)]+)', r'^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)',
                r'(?:href|src)\s*=\s*["\']([^"\']+)', r'<(https?://[^>]+)>',
                r'(?<!["\'])\b(https?://[^\s<>]+)']
    return {match.strip('<>').rstrip(').,') for pattern in patterns
            for match in re.findall(pattern, text, flags=re.MULTILINE | re.IGNORECASE)}


def forbidden_link(page, target, patterns):
    target = unquote(target).replace('\\', '/')
    parsed = urlsplit(target)
    if parsed.scheme:
        if parsed.scheme not in ('http', 'https', 'file') and not re.match(r'^[A-Za-z]:/', target):
            return False
        # Recognize repository paths even after a blob/tree revision component.
        parts = parsed.path.strip('/').split('/')
        return any(is_private('/'.join(parts[i:]), patterns) for i in range(len(parts)))
    path = parsed.path
    if not path:
        return False
    resolved = os.path.normpath(path.lstrip('/') if path.startswith('/') else str(page.parent / path))
    return is_private(resolved, patterns)


def check(root):
    root = Path(root).resolve()
    patterns = private_patterns(root)
    failures = []
    for path in files(root):
        if is_private(path, patterns):
            failures.append(f'Published local-only file: {path.as_posix()}')
            continue
        if path.suffix.lower() not in ('.md', '.html', '.rst') or not (root / path).is_file():
            continue
        for target in sorted(links((root / path).read_text(encoding='utf-8'))):
            if forbidden_link(path, target, patterns):
                failures.append(f'{path.as_posix()} -> {target}')
    if failures:
        raise ValueError('Private publication/reference violation:\n' + '\n'.join(failures))


if __name__ == '__main__':
    check(Path(__file__).resolve().parents[1])
    print('PASS: public files and references respect local-development filters')
