#!/usr/bin/env python3
"""Две формы PDF-отчёта о проверках из явного нейтрального JSON (schema 2).

Компактный обзор — что проверено, где, когда и с каким итогом; технический отчёт —
маршрут «требование → сценарии → измерения → графики → вывод» по карточкам
свидетельств. Генератор не читает стенд и не вычисляет применимость: он проверяет
связи и нейтральность входа, нумерует разделы, рисунки и ссылки и вёрстает PDF.

  python render_report.py --input report.json --output build/report-0.1.0
  python render_report.py --input report.json --output build/r --font Arial.ttf --font-bold Arialbd.ttf

Выход: compact.pdf, technical.pdf, figures/*.png, provenance.json. Каталог должен быть новым.
Код возврата: 0 — готово, 2 — вход не прошёл проверку (причины печатаются).
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from xml.sax.saxutils import escape

SCHEMA = 2
STATUSES = ("PASS", "FAIL", "ERROR", "SKIP", "UNKNOWN", "PLANNED")
TIMEZONE = re.compile(r"\b(?:UTC|GMT)\s*[+−-]\s*\d{1,2}\b|\bUTC\b")
# Признаки инфраструктурных идентификаторов, которым не место в нейтральном отчёте.
IDENTIFIERS = (
    ("IPv4-адрес", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
    ("MAC-адрес", re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")),
    ("серийный номер (hex)", re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{20,32}(?![0-9A-Fa-f])")),
    ("путь Windows", re.compile(r"\b[A-Za-z]:[\\/]")),
    ("домашний каталог", re.compile(r"(?:/home/|/Users/|\\Users\\|~/)")),
    ("устройство Linux", re.compile(r"/dev/(?:tty|serial)")),
    ("почта", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
    ("номер в поле serial", re.compile(r"(?i)\bserial\s*[=:]\s*\S+")),
)


class InputError(ValueError):
    pass


# ---------------------------------------------------------------- проверка входа

def text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise InputError("нужен непустой текст: %s" % where)
    return value


def strings(value, path=""):
    """Все строки входа с их путями — для проверки нейтральности."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key == "sha256":
                continue
            yield from strings(item, "%s.%s" % (path, key) if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, "%s[%d]" % (path, index))


def neutral_issues(data):
    issues = []
    for path, value in strings(data):
        for name, pattern in IDENTIFIERS:
            match = pattern.search(value)
            if match:
                issues.append("%s: %s «%s»" % (path, name, match.group(0)))
    return issues


def check_table(table, where):
    columns, rows = table.get("columns"), table.get("rows")
    if not isinstance(columns, list) or not columns or not isinstance(rows, list) or not rows:
        raise InputError("%s: таблица без колонок или строк" % where)
    if any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
        raise InputError("%s: ширина строки не совпадает с числом колонок" % where)
    widths = table.get("widths")
    if widths is not None and (len(widths) != len(columns) or abs(sum(widths) - 1) > 0.02):
        raise InputError("%s: widths — доли ширины по числу колонок, сумма 1" % where)


def check_chart(chart, where):
    kind = chart.get("kind", "line")
    if kind not in ("line", "step", "bar"):
        raise InputError("%s: kind — line, step или bar" % where)
    text(chart.get("x_label"), where + ".x_label")
    text(chart.get("y_label"), where + ".y_label")
    text(chart.get("caption"), where + ".caption")
    series = chart.get("series")
    if not isinstance(series, list) or not series:
        raise InputError("%s: нет рядов" % where)
    size = len(chart["categories"]) if kind == "bar" else None
    if kind == "bar" and not chart.get("categories"):
        raise InputError("%s: столбцам нужны categories" % where)
    for number, item in enumerate(series):
        name = "%s.series[%d]" % (where, number)
        text(item.get("label"), name + ".label")
        ys = item.get("y")
        xs = item.get("x") if kind != "bar" else list(range(size))
        if not isinstance(ys, list) or len(ys) < (1 if kind == "bar" else 2) or len(xs or []) != len(ys):
            raise InputError("%s: x и y одной длины (не меньше двух точек)" % name)
        # Отсутствующее значение — не ноль: такой ряд не рисуется.
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in list(xs) + list(ys)):
            raise InputError("%s: в ряду есть отсутствующие или нечисловые значения" % name)
    band = chart.get("band")
    if band is not None and not (type(band.get("low")) in (int, float) and type(band.get("high")) in (int, float)
                                 and band["low"] < band["high"] and isinstance(band.get("label"), str)):
        raise InputError("%s: band — low < high и подпись источника допуска" % where)


def validate(data):
    """Связи, обязательные поля, часовой пояс и нейтральность; возвращает список проблем нейтральности."""
    if data.get("schema") != SCHEMA:
        raise InputError("schema должен быть %d" % SCHEMA)
    if type(data.get("demonstration")) is not bool:
        raise InputError("demonstration — явное true или false")
    for key in ("object", "footer"):
        text(data.get(key), key)
    compact, technical = data.get("compact"), data.get("technical")
    if not isinstance(compact, dict) or not isinstance(technical, dict):
        raise InputError("нужны разделы compact и technical")
    for form, name in ((compact, "compact"), (technical, "technical")):
        for key in ("title", "subtitle", "date"):
            text(form.get(key), "%s.%s" % (name, key))
        if not TIMEZONE.search(form["date"]):
            raise InputError("%s.date: укажите часовой пояс (UTC+N или GMT+N)" % name)
    if not compact.get("main"):
        raise InputError("compact.main: нужен раздел «Главное»")
    check_table({"columns": ["Что", "Состав"], "rows": compact.get("conditions") or []}, "compact.conditions")
    for number, section in enumerate(compact.get("sections", [])):
        text(section.get("title"), "compact.sections[%d].title" % number)
        check_table(section, "compact.sections[%d]" % number)
    if not compact.get("not_checked"):
        raise InputError("compact.not_checked: перечислите, что не проверялось")
    methods = technical.get("methods") or []
    method_ids = [m.get("id") for m in methods]
    if not methods or len(set(method_ids)) != len(method_ids):
        raise InputError("technical.methods: нужны способы съёма с уникальными id")
    for number, item in enumerate(methods):
        for key in ("id", "name", "gives", "accuracy"):
            text(item.get(key), "technical.methods[%d].%s" % (number, key))
    evidence = technical.get("evidence") or []
    if not evidence:
        raise InputError("technical.evidence: нет карточек")
    ids, remark_ids = [], []
    for number, card in enumerate(evidence):
        where = "technical.evidence[%d]" % number
        for key in ("id", "title", "requirement", "scenarios", "shows", "conditions", "conclusion", "data"):
            text(card.get(key), "%s.%s" % (where, key))
        if card.get("status") not in STATUSES:
            raise InputError("%s.status — одно из %s" % (where, ", ".join(STATUSES)))
        refs = card.get("method_ids")
        if not refs or any(ref not in method_ids for ref in refs):
            raise InputError("%s.method_ids: неизвестный способ съёма" % where)
        ids.append(card["id"])
        if not card.get("tables") and not card.get("charts"):
            raise InputError("%s: нужны таблица или график" % where)
        for t_number, table in enumerate(card.get("tables", [])):
            check_table(table, "%s.tables[%d]" % (where, t_number))
        for c_number, chart in enumerate(card.get("charts", [])):
            check_chart(chart, "%s.charts[%d]" % (where, c_number))
        if not TIMEZONE.search(card["data"]):
            raise InputError("%s.data: время свидетельства без часового пояса" % where)
        for r_number, remark in enumerate(card.get("remarks", [])):
            for key in ("id", "title", "status", "observed", "why", "proposal"):
                text(remark.get(key), "%s.remarks[%d].%s" % (where, r_number, key))
            remark_ids.append(remark["id"])
    for item in technical.get("planned", []):
        for key in ("id", "shows", "method", "reason"):
            text(item.get(key), "technical.planned.%s" % key)
        ids.append(item["id"])
    if len(set(ids)) != len(ids) or len(set(remark_ids)) != len(remark_ids):
        raise InputError("повторный код свидетельства или замечания")
    if not technical.get("excluded"):
        raise InputError("technical.excluded: раздел «Что не вошло» обязателен")
    check_table({"columns": ["Что", "Почему"], "rows": technical["excluded"]}, "technical.excluded")
    provenance = technical.get("provenance")
    if not isinstance(provenance, dict):
        raise InputError("technical.provenance: нужно приложение происхождения")
    text(provenance.get("text"), "technical.provenance.text")
    check_table(provenance, "technical.provenance")
    return neutral_issues(data)


# ---------------------------------------------------------------- стиль

def setup_fonts(regular, bold, italic, mono):
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("R", regular))
    pdfmetrics.registerFont(TTFont("R-B", bold))
    pdfmetrics.registerFont(TTFont("R-I", italic or regular))
    pdfmetrics.registerFont(TTFont("R-BI", bold))
    pdfmetrics.registerFont(TTFont("R-M", mono or regular))
    addMapping("R", 0, 0, "R")
    addMapping("R", 1, 0, "R-B")
    addMapping("R", 0, 1, "R-I")
    addMapping("R", 1, 1, "R-BI")


def find_font(names):
    for folder in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts", "/Library/Fonts",
                   "/usr/share/fonts/TTF", "/usr/share/fonts/dejavu"):
        for name in names:
            path = Path(folder) / name
            if path.is_file():
                return str(path)
    return None


class Style(object):
    """Палитра и размеры выпускных отчётов: тёмно-синие заголовки, светло-голубые шапки таблиц."""

    def __init__(self):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        self.mm = mm
        self.blue = colors.HexColor("#1F4E79")
        self.head_bg = colors.HexColor("#DCE6F2")
        self.grid = colors.HexColor("#9DB3CC")
        self.req_bg, self.req_bar = colors.HexColor("#EEF3FA"), colors.HexColor("#3B6EA8")
        self.note_bg, self.note_bar = colors.HexColor("#FDF0E6"), colors.HexColor("#E07020")
        self.grey = colors.HexColor("#555555")
        self.width, self.height = A4
        self.margin = 18 * mm
        self.content = self.width - 2 * self.margin

        def ps(name, **kw):
            return ParagraphStyle(name, fontName=kw.pop("font", "R"), **kw)
        self.s = {
            "title": ps("title", font="R-B", fontSize=19, leading=24, textColor=self.blue, spaceAfter=4),
            "sub": ps("sub", fontSize=10.5, leading=14, spaceAfter=3),
            "date": ps("date", font="R-B", fontSize=10.5, leading=14, textColor=self.blue, spaceBefore=3, spaceAfter=4),
            "src": ps("src", font="R-I", fontSize=8.2, leading=11, textColor=self.grey, spaceAfter=3),
            "h1": ps("h1", font="R-B", fontSize=12.5, leading=16, textColor=self.blue, spaceBefore=10, spaceAfter=5,
                     keepWithNext=1),
            "body": ps("body", fontSize=8.6, leading=11.6, spaceAfter=3),
            "bullet": ps("bullet", fontSize=8.6, leading=11.6, leftIndent=10, bulletIndent=0, spaceAfter=1.5),
            "cell": ps("cell", fontSize=7.6, leading=9.6),
            "cellb": ps("cellb", font="R-B", fontSize=7.6, leading=9.6),
            "cellm": ps("cellm", font="R-M", fontSize=6.9, leading=8.8),
            "cap": ps("cap", font="R-I", fontSize=7.8, leading=10, textColor=self.grey, spaceBefore=2, spaceAfter=6),
            "data": ps("data", fontSize=7.2, leading=9.2, textColor=self.grey, spaceAfter=4),
            "req": ps("req", font="R-I", fontSize=8.2, leading=11),
            "note": ps("note", fontSize=8.2, leading=11),
        }

    def p(self, value, style="body"):
        from reportlab.platypus import Paragraph
        return Paragraph(value, self.s[style])

    def bullets(self, items):
        from reportlab.platypus import Paragraph
        return [Paragraph(escape(item), self.s["bullet"], bulletText="•") for item in items]

    def table(self, columns, rows, widths=None, mono=()):
        """Шапка — светло-голубая заливка и полужирный текст, тонкая сетка, шапка повторяется на новой странице."""
        from reportlab.platypus import Table, TableStyle
        widths = widths or [1.0 / len(columns)] * len(columns)
        data = [[self.p(escape(str(c)), "cellb") for c in columns]]
        for row in rows:
            data.append([self.p(escape(str(c)), "cellm" if j in mono else "cell") for j, c in enumerate(row)])
        table = Table(data, colWidths=[w * self.content for w in widths], repeatRows=1)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, self.grid), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, 0), self.head_bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        return table

    def requirement(self, value):
        from reportlab.platypus import Table, TableStyle
        table = Table([[self.p(escape(value), "req")]], colWidths=[self.content])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.req_bg), ("LINEBEFORE", (0, 0), (0, -1), 3, self.req_bar),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return table

    def remark(self, item):
        from reportlab.platypus import KeepTogether, Spacer, Table, TableStyle
        head = "<b>Замечание %s · %s%s, %s</b>" % (escape(item["id"]), escape(item["title"]),
                                                   (" · " + escape(item["ref"])) if item.get("ref") else "",
                                                   escape(item["status"]))
        rows = [[self.p(head, "note")], [self.p("Наблюдение: " + escape(item["observed"]), "note")],
                [self.p("Почему важно: " + escape(item["why"]), "note")],
                [self.p("Предложение: " + escape(item["proposal"]), "note")]]
        table = Table(rows, colWidths=[self.content - 2])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.note_bg), ("BOX", (0, 0), (-1, -1), 1, self.note_bar),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
        return KeepTogether([Spacer(1, 3), table, Spacer(1, 4)])

    def figure(self, path, caption):
        from reportlab.platypus import Image, KeepTogether
        from reportlab.lib.utils import ImageReader
        width, height = ImageReader(str(path)).getSize()
        drawn = self.content
        return KeepTogether([Image(str(path), width=drawn, height=drawn * height / width), self.p(caption, "cap")])

    def build(self, path, story, footer, title):
        from reportlab.platypus import SimpleDocTemplate

        def page(canvas, doc):
            canvas.saveState()
            canvas.setFont("R", 7)
            canvas.setFillColor(self.grey)
            canvas.drawString(self.margin, 10 * self.mm, footer)
            canvas.drawRightString(self.width - self.margin, 10 * self.mm, "Стр. %d" % doc.page)
            canvas.restoreState()
        doc = SimpleDocTemplate(str(path), pagesize=(self.width, self.height), leftMargin=self.margin,
                                rightMargin=self.margin, topMargin=16 * self.mm, bottomMargin=18 * self.mm,
                                title=title, author="", creator="", subject="", keywords="")
        doc.build(story, onFirstPage=page, onLaterPages=page)


# ---------------------------------------------------------------- графики

def number(value):
    return ("%g" % value).replace(".", ",").replace("-", "−")


def draw_chart(chart, path, font):
    """Ожидание — синий, наблюдение — оранжевый, полоса допуска — светло-зелёная с подписью источника."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    font_manager.fontManager.addfont(font)
    family = font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({
        "font.family": family, "font.size": 9, "axes.labelsize": 9, "axes.facecolor": "#FAFAF7",
        "figure.facecolor": "white", "axes.edgecolor": "#BBBBBB", "axes.grid": True, "grid.color": "#E3E3E3",
        "grid.linewidth": 0.7, "legend.fontsize": 8, "legend.frameon": False, "axes.spines.top": False,
        "axes.spines.right": False})
    roles = {"expected": "#2A6FDB", "observed": "#E8692E"}
    extra = ["#3A8F5C", "#8E5AB5", "#777777", "#B8860B"]
    fig, ax = plt.subplots(figsize=(7.2, chart.get("height", 2.4)))
    band = chart.get("band")
    kind = chart.get("kind", "line")
    if band:
        ax.axhspan(band["low"], band["high"], color="#DFF0E2", alpha=0.7, lw=0, label=band["label"])
    if kind == "bar":
        categories = chart["categories"]
        count = len(chart["series"])
        step = 0.8 / count
        for index, item in enumerate(chart["series"]):
            color = roles.get(item.get("role"), extra[index % len(extra)])
            xs = [i - 0.4 + step * (index + 0.5) for i in range(len(categories))]
            bars = ax.bar(xs, item["y"], width=step * 0.92, color=color, label=item["label"])
            # Нулевое наблюдение подписывается: отсутствие столбца не должно читаться как «нет данных».
            for bar, value in zip(bars, item["y"]):
                ax.annotate(number(value), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                            ha="center", va="bottom", fontsize=7, xytext=(0, 1), textcoords="offset points")
        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories)
        ax.grid(axis="x", visible=False)
    else:
        for index, item in enumerate(chart["series"]):
            color = roles.get(item.get("role"), extra[index % len(extra)])
            style = "--" if item.get("role") == "expected" else "-"
            if kind == "step":
                ax.step(item["x"], item["y"], where="post", color=color, lw=1.6, ls=style, label=item["label"])
            else:
                marker = "o" if len(item["x"]) <= 30 else None
                ax.plot(item["x"], item["y"], color=color, lw=1.6, ls=style, marker=marker, ms=3.5,
                        label=item["label"])
    for note in chart.get("annotations", []):
        ax.annotate(note["text"], (note["x"], note["y"]), fontsize=7.5, color="#333333",
                    xytext=(note.get("dx", 6), note.get("dy", 6)), textcoords="offset points")
    formatter = ticker.FuncFormatter(lambda v, _: number(v))
    ax.yaxis.set_major_formatter(formatter)
    if kind != "bar":
        ax.xaxis.set_major_formatter(formatter)
    ax.set_xlabel(chart["x_label"])
    ax.set_ylabel(chart["y_label"])
    if len(chart["series"]) > 1 or band:
        # Легенда над полем графика: не закрывает данные и полосу допуска.
        entries = len(chart["series"]) + (1 if band else 0)
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=min(entries, 4), borderaxespad=0)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- формы

def compact_story(data, st):
    form = data["compact"]
    story = [st.p(escape(form["title"]).replace("\n", "<br/>"), "title"), st.p(escape(form["subtitle"]), "sub"),
             st.p(escape(form["date"]), "date")]
    if form.get("source"):
        story.append(st.p(escape(form["source"]), "src"))
    section = 1
    story.append(st.p("%d. Главное" % section, "h1"))
    story += st.bullets(form["main"])
    section += 1
    story += [st.p("%d. Объект и условия проверки" % section, "h1"),
              st.table(["Что", "Состав"], form["conditions"], [0.18, 0.82])]
    for item in form.get("sections", []):
        section += 1
        story += [st.p("%d. %s" % (section, escape(item["title"])), "h1"),
                  st.table(item["columns"], item["rows"], item.get("widths"))]
        if item.get("note"):
            story.append(st.p(escape(item["note"]), "src"))
    section += 1
    story.append(st.p("%d. Что не проверялось" % section, "h1"))
    story += st.bullets(form["not_checked"])
    return story


def technical_story(data, st, figures, font):
    from reportlab.platypus import KeepTogether
    form = data["technical"]
    evidence = form["evidence"]
    planned = form.get("planned", [])
    first_card = 4
    sections = {card["id"]: first_card + n for n, card in enumerate(evidence)}
    summary = first_card + len(evidence)
    excluded = summary + 1
    story = [st.p(escape(form["title"]).replace("\n", "<br/>"), "title"), st.p(escape(form["subtitle"]), "sub"),
             st.p(escape(form["date"]), "date")]
    standard = ("Каждое свидетельство отвечает на пункты требований данными, снятыми сценариями. В нём: формулировка "
                "требования (синяя плашка), условия и способ съёма, таблица ключевых чисел, графики с номиналами и "
                "допусками, вывод и то, что не проверено, строка «Данные» со временем прогонов. Замечание для "
                "разработчика стоит сразу под свидетельством в оранжевой рамке с кодом З-NN; сводка — в разделе %d, "
                "происхождение данных — в приложении A." % summary)
    story += [st.p("1. Как читать отчёт", "h1"), st.p(standard)]
    story += [st.p(escape(item)) for item in form.get("how_to_read", [])]
    if data["demonstration"]:
        story.append(st.requirement("Демонстрационные данные для макета отчёта: это не результат испытаний."))
    used = {m["id"]: [c["id"] for c in evidence if m["id"] in c["method_ids"]] for m in form["methods"]}
    rows = [[m["id"], m["name"], m["gives"], m["accuracy"], ", ".join(used[m["id"]]) or "—"] for m in form["methods"]]
    story += [st.p("2. Способы съёма и их точность", "h1"),
              st.table(["Код", "Способ", "Что даёт", "Точность и ограничения", "Где применён"], rows,
                       [0.07, 0.23, 0.22, 0.30, 0.18])]
    if form.get("methods_note"):
        story.append(st.p(escape(form["methods_note"])))
    rows = [[c["id"], c["requirement_ref"] if c.get("requirement_ref") else "—", c["scenarios"], c["shows"],
             ", ".join(c["method_ids"]), str(sections[c["id"]])] for c in evidence]
    rows += [[p["id"], p.get("requirement_ref", "—"), "—", p["shows"], p["method"], "нет: " + p["reason"]]
             for p in planned]
    story += [st.p("3. Перечень свидетельств", "h1"),
              st.table(["№", "Требование", "Сценарии", "Что показывает", "Способ", "Раздел"], rows,
                       [0.07, 0.15, 0.26, 0.28, 0.11, 0.13])]
    figure_number = 0
    remarks = []
    for card in evidence:
        story += [st.p("%d. %s. %s" % (sections[card["id"]], escape(card["id"]), escape(card["title"])), "h1"),
                  st.requirement(card["requirement"]),
                  st.p("<b>Условия и способ.</b> " + escape(card["conditions"]))]
        for table in card.get("tables", []):
            story.append(st.table(table["columns"], table["rows"], table.get("widths"), tuple(table.get("mono", []))))
            if table.get("note"):
                story.append(st.p(escape(table["note"]), "src"))
        for chart in card.get("charts", []):
            figure_number += 1
            path = figures / ("fig-%02d.png" % figure_number)
            draw_chart(chart, path, font)
            story.append(st.figure(path, "Рис. %d. %s" % (figure_number, escape(chart["caption"]))))
        story.append(st.p("<b>Вывод.</b> " + escape(card["conclusion"])))
        if card.get("not_checked"):
            story.append(st.p("<b>Не проверено.</b> " + escape(card["not_checked"])))
        story.append(st.p("Данные: " + escape(card["data"]), "data"))
        for item in card.get("remarks", []):
            story.append(st.remark(item))
            remarks.append([item["id"], item["title"], card["id"], item["status"]])
    rows = remarks + [list(r) for r in form.get("closed_remarks", [])]
    story.append(st.p("%d. Сводка замечаний" % summary, "h1"))
    story.append(st.table(["Код", "Где", "Свидетельство", "Статус"], rows, [0.12, 0.42, 0.16, 0.30])
                 if rows else st.p("Замечаний нет."))
    story += [st.p("%d. Что не вошло" % excluded, "h1"), st.table(["Что", "Почему"], form["excluded"], [0.42, 0.58])]
    provenance = form["provenance"]
    appendix = [st.p("Приложение A. Происхождение данных", "h1"), st.p(escape(provenance["text"])),
                st.table(provenance["columns"], provenance["rows"], provenance.get("widths"),
                         tuple(provenance.get("mono", [])))]
    if provenance.get("note"):
        appendix.append(st.p(escape(provenance["note"]), "data"))
    # Короткое приложение держится целиком: последняя строка не уходит одна на пустую страницу.
    story += [KeepTogether(appendix)] if len(provenance["rows"]) <= 20 else appendix
    return story


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", help="шрифт с кириллицей (по умолчанию DejaVu Sans или Arial)")
    parser.add_argument("--font-bold")
    parser.add_argument("--font-italic")
    parser.add_argument("--font-mono")
    parser.add_argument("--allow-identifiers", action="store_true",
                        help="не останавливаться на признаках серийников, адресов и путей (внутренний отчёт)")
    parser.add_argument("--check-only", action="store_true", help="только проверить вход")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = json.loads(raw)
    try:
        issues = validate(data)
    except InputError as error:
        print("Вход не прошёл проверку: %s" % error, file=sys.stderr)
        return 2
    if issues and not args.allow_identifiers:
        print("Вход не нейтрален (замените ролями: стенд, лаборатория, отладчик, узел стенда):", file=sys.stderr)
        for line in issues:
            print("  " + line, file=sys.stderr)
        return 2
    if args.check_only:
        print("вход корректен")
        return 0
    regular = args.font or find_font(("DejaVuSans.ttf", "arial.ttf", "Arial.ttf"))
    bold = args.font_bold or find_font(("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"))
    if not regular or not bold:
        print("Нужен шрифт с кириллицей: --font и --font-bold", file=sys.stderr)
        return 2
    italic = args.font_italic or find_font(("DejaVuSans-Oblique.ttf", "ariali.ttf", "Arial Italic.ttf"))
    mono = args.font_mono or find_font(("DejaVuSansMono.ttf", "consola.ttf", "cour.ttf"))
    if args.output.exists():
        print("Каталог уже существует: %s" % args.output, file=sys.stderr)
        return 2
    figures = args.output / "figures"
    figures.mkdir(parents=True)
    setup_fonts(regular, bold, italic, mono)
    st = Style()
    st.build(args.output / "compact.pdf", compact_story(data, st), data["footer"], data["compact"]["title"])
    st.build(args.output / "technical.pdf", technical_story(data, st, figures, regular), data["footer"],
             data["technical"]["title"])
    me = Path(__file__).resolve()
    (args.output / "provenance.json").write_text(json.dumps({
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "generator_sha256": hashlib.sha256(me.read_bytes()).hexdigest(),
        "schema": SCHEMA, "demonstration": data["demonstration"], "neutral": not issues,
        "outputs": ["compact.pdf", "technical.pdf"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output / "compact.pdf")
    print(args.output / "technical.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
