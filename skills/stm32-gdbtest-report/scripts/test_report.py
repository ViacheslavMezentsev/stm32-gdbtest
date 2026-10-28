"""Самопроверка навыка: связи входа, нейтральность, отказ на пропусках и рендер обеих форм."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render_report import InputError, neutral_issues, validate  # noqa: E402

REFERENCES = HERE.parent / "references"


def load(name):
    return json.loads((REFERENCES / name).read_text(encoding="utf-8"))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.data = load("example.json")

    def test_examples_are_valid_and_neutral(self):
        for name in ("example.json", "acceptance-050.json"):
            with self.subTest(name=name):
                self.assertEqual(validate(load(name)), [])

    def test_unknown_method_and_duplicates(self):
        data = copy.deepcopy(self.data)
        data["technical"]["evidence"][0]["method_ids"] = ["М-9"]
        with self.assertRaisesRegex(InputError, "способ"):
            validate(data)
        data = copy.deepcopy(self.data)
        data["technical"]["evidence"].append(copy.deepcopy(data["technical"]["evidence"][1]))
        with self.assertRaisesRegex(InputError, "повторный"):
            validate(data)

    def test_timezone_required(self):
        for path in (("compact", "date"), ("technical", "date")):
            data = copy.deepcopy(self.data)
            data[path[0]][path[1]] = "Дата и время проверок: 27.10.2026"
            with self.subTest(path=path), self.assertRaisesRegex(InputError, "часовой пояс"):
                validate(data)
        data = copy.deepcopy(self.data)
        data["technical"]["evidence"][0]["data"] = "плата А — CHARGE_SWEEP 16:10"
        with self.assertRaisesRegex(InputError, "часового пояса"):
            validate(data)

    def test_missing_values_are_not_zero(self):
        data = copy.deepcopy(self.data)
        data["technical"]["evidence"][0]["charts"][0]["series"][0]["y"][3] = None
        with self.assertRaisesRegex(InputError, "отсутствующие"):
            validate(data)

    def test_table_width_and_required_sections(self):
        data = copy.deepcopy(self.data)
        data["technical"]["evidence"][1]["tables"][0]["rows"][0].pop()
        with self.assertRaisesRegex(InputError, "ширина строки"):
            validate(data)
        for key in ("not_checked", "main"):
            data = copy.deepcopy(self.data)
            data["compact"][key] = []
            with self.subTest(key=key), self.assertRaises(InputError):
                validate(data)

    def test_identifiers_are_detected(self):
        samples = {"IPv4-адрес": "узел 192.168.1.20", "серийный номер (hex)": "пробник 066CFF494849877187252626",
                   "путь Windows": "файл D:\\work\\rec.bag", "домашний каталог": "/home/user/rec.bag",
                   "устройство Linux": "/dev/ttyACM0", "почта": "a.b@example.org"}
        for name, value in samples.items():
            data = copy.deepcopy(self.data)
            data["compact"]["main"][0] = value
            with self.subTest(name=name):
                self.assertTrue(any(name in issue for issue in neutral_issues(data)), name)
        data = copy.deepcopy(self.data)
        data["technical"]["provenance"]["rows"][0][4] = "a" * 40
        self.assertEqual(neutral_issues(data), [], "хеш коммита и SHA-256 содержимого допустимы")

    def test_render_both_forms(self):
        import importlib.util
        if not all(importlib.util.find_spec(name) for name in ("reportlab", "matplotlib")):
            self.skipTest("нужны reportlab и matplotlib")
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "report"
            proc = subprocess.run([sys.executable, str(HERE / "render_report.py"), "--input",
                                   str(REFERENCES / "example.json"), "--output", str(out)],
                                  capture_output=True, text=True, timeout=300)
            if proc.returncode == 2 and "шрифт" in proc.stderr:
                self.skipTest("нет шрифта с кириллицей")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            for name in ("compact.pdf", "technical.pdf"):
                self.assertTrue((out / name).read_bytes().startswith(b"%PDF"))
            self.assertEqual(len(list((out / "figures").glob("*.png"))), 3)
            provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
            self.assertTrue(provenance["neutral"] and provenance["demonstration"])
            if shutil.which("pdftotext"):
                text = subprocess.run(["pdftotext", str(out / "technical.pdf"), "-"], capture_output=True,
                                      text=True).stdout
                text = " ".join(text.split())
                for marker in ("1. Как читать отчёт", "2. Способы съёма и их точность", "3. Перечень свидетельств",
                               "4. С-01. Канал напряжения АКБ", "Рис. 3.", "Замечание З-01", "7. Сводка замечаний",
                               "8. Что не вошло", "Приложение A. Происхождение данных", "нет: доработка"):
                    self.assertIn(marker, text)
            again = subprocess.run([sys.executable, str(HERE / "render_report.py"), "--input",
                                    str(REFERENCES / "example.json"), "--output", str(out)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(again.returncode, 2, "существующий каталог не перезаписывается")

    def test_render_refuses_identifiers(self):
        data = copy.deepcopy(self.data)
        data["compact"]["source"] = "Источник: узел 10.0.0.5"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "in.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(HERE / "render_report.py"), "--check-only", "--input", str(path),
                                   "--output", str(Path(temp) / "out")], capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("IPv4", proc.stderr)


if __name__ == "__main__":
    unittest.main()
