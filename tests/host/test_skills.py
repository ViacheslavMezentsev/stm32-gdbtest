"""Agent skills in skills/: the SKILL.md header is valid YAML with a name and a description.

GitHub and agents parse the header strictly; a plain scalar must not contain ": " or " #".
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


def problems(path):
    found, keys = [], {}
    for line in header(path).splitlines():
        key, separator, value = line.partition(": ")
        if not separator or not re.fullmatch(r"[a-z_]+", key):
            found.append(f"not a single-line key: {line[:40]}")
            continue
        keys[key] = value
        # A plain scalar ends at ": " or " #" and cannot start with a YAML indicator.
        if ": " in value or " #" in value or value[:1] in "&*!|>'\"%@`{[":
            found.append(f"{key}: plain scalar with a YAML indicator")
    if sorted(keys) != ["description", "name"]:
        found.append(f"keys {sorted(keys)}, want description and name")
    if keys.get("name") != path.parent.name or not NAME.fullmatch(keys.get("name", "")):
        found.append("name must equal the kebab-case directory name")
    if not 0 < len(keys.get("description", "")) <= 1024:
        found.append("description must hold 1..1024 characters")
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
        path.write_text("---\nname: skill-sample\ndescription: run it; EN: run\n---\n", encoding="utf-8")
        try:
            self.assertTrue(any("YAML indicator" in text for text in problems(path)))
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
