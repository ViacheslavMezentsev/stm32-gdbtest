"""Agent skills in skills/: the SKILL.md header follows the Agent Skills specification.

Format as in demo-stm32-skills: name (the directory), description, license: MIT, compatibility and
metadata (author, version and further string values); allowed-tools is optional. GitHub and agents
parse the header strictly, so a plain scalar must not contain ": " or " #". CI also runs the pinned
skills-ref validator (docs workflow); this test keeps the rules checkable offline.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def header(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("no YAML header")
    return text[4:text.index("\n---\n", 4)]


REQUIRED = ["compatibility", "description", "license", "metadata", "name"]
OPTIONAL = ["allowed-tools"]
METADATA = ["author", "version"]


def plain(key, value):
    """A plain scalar ends at ": " or " #" and cannot start with a YAML indicator."""
    if ": " in value or " #" in value or value[:1] in "&*!|>'\"%@`{[":
        return [f"{key}: plain scalar with a YAML indicator"]
    return []


def problems(path):
    found, keys, metadata, block = [], {}, {}, None
    for line in header(path).splitlines():
        if block == "metadata" and line.startswith("  "):
            key, separator, value = line[2:].partition(": ")
            if not separator or not re.fullmatch(r"[a-z_]+", key):
                found.append(f"metadata: not a single-line key: {line[:40]}")
                continue
            # Metadata values are strings: quote values that YAML would read as numbers.
            if re.fullmatch(r'"[^"]*"', value):
                value = value[1:-1]
            elif re.fullmatch(r"[0-9.]+", value):
                found.append(f"metadata.{key}: quote the value so that it stays a string")
            else:
                found += plain(f"metadata.{key}", value)
            metadata[key] = value
            continue
        block = None
        if line == "metadata:":
            block = keys["metadata"] = "metadata"
            continue
        key, separator, value = line.partition(": ")
        if not separator or not re.fullmatch(r"[a-z][a-z-]*", key):
            found.append(f"not a single-line key: {line[:40]}")
            continue
        keys[key] = value
        found += plain(key, value)
    if sorted(set(keys) - set(OPTIONAL)) != REQUIRED or set(keys) - set(REQUIRED) - set(OPTIONAL):
        found.append(f"keys {sorted(keys)}, want {REQUIRED} and optionally {OPTIONAL}")
    if keys.get("name") != path.parent.name or not NAME.fullmatch(keys.get("name", "")):
        found.append("name must equal the kebab-case directory name")
    if not 0 < len(keys.get("name", "")) <= 64:
        found.append("name must hold 1..64 characters")
    if not 0 < len(keys.get("description", "")) <= 1024:
        found.append("description must hold 1..1024 characters")
    if keys.get("license") != "MIT":
        found.append("license must be MIT")
    if not 0 < len(keys.get("compatibility", "")) <= 500:
        found.append("compatibility must hold 1..500 characters")
    if [key for key in METADATA if not metadata.get(key)]:
        found.append(f"metadata needs {METADATA}")
    if len(path.read_text(encoding="utf-8").splitlines()) > 500:
        found.append("SKILL.md longer than 500 lines: move details to references/")
    try:
        import yaml
    except ImportError:
        return found
    try:
        data = yaml.safe_load(header(path))
    except yaml.YAMLError as error:
        return found + [f"PyYAML: {str(error).splitlines()[0]}"]
    if not isinstance(data, dict) or data.get("name") != keys.get("name"):
        found.append("PyYAML reads a different header")
    elif not all(isinstance(value, str) for value in (data.get("metadata") or {}).values()):
        found.append("PyYAML reads a metadata value that is not a string")
    return found


class SkillTests(unittest.TestCase):
    def test_skill_headers(self):
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 3)
        report = [f"{path.relative_to(ROOT)}: {text}" for path in skills for text in problems(path)]
        self.assertEqual(report, [], "\n".join(report))

    def test_the_check_sees_a_colon(self):
        path = ROOT / "build" / "skill-sample" / "skill-sample" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: skill-sample\ndescription: run it; EN: run\nlicense: MIT\ncompatibility: any\n"
                        "metadata:\n  author: A\n  version: \"1\"\n---\n", encoding="utf-8")
        try:
            self.assertTrue(any("YAML indicator" in text for text in problems(path)))
        finally:
            path.unlink()

    def test_the_check_wants_string_metadata(self):
        path = ROOT / "build" / "skill-sample" / "skill-sample" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: skill-sample\ndescription: run it\nlicense: MIT\ncompatibility: any\n"
                        "metadata:\n  author: A\n  version: 1.0\n---\n", encoding="utf-8")
        try:
            self.assertTrue(any("quote the value" in text for text in problems(path)))
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
