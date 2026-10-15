"""Portable source viewer and standard coverage formats; no target access."""
from collections import defaultdict
from datetime import datetime
from html import escape
import json
from pathlib import Path
from urllib.parse import quote

def github(repository, sha, path, line):
    return f"https://github.com/{repository}/blob/{sha}/{quote(path, safe='/')}#L{line}"

import xml.etree.ElementTree as ET

def line_state(points):
    states = {p["state"] for p in points}
    if "FAILED" in states:
        return "FAILED"
    if "UNKNOWN" in states:
        return "UNKNOWN"
    return "CONFIRMED" if states else "UNMAPPED"


def formats(public):
    grouped, marks = defaultdict(list), defaultdict(dict)
    for p in public["points"]:
        grouped[(p["source"], p["line"])].append(p)
    for (source, line), points in grouped.items():
        state = line_state(points)
        if state in ("CONFIRMED", "FAILED"):
            marks[source][line] = int(state == "CONFIRMED")
    # UNKNOWN не превращается в 0; смешанная confirmed/unknown строка исключается целиком.
    total = sum(len(m) for m in marks.values())
    covered = sum(sum(m.values()) for m in marks.values())
    coverage = ET.Element("coverage", {"line-rate": str(covered / total if total else 0),
        "branch-rate": "0", "lines-covered": str(covered), "lines-valid": str(total),
        "branches-covered": "0", "branches-valid": "0", "complexity": "0",
        "version": "DDTT-boolean", "timestamp": str(max([int(datetime.fromisoformat(p["started_utc"]).timestamp())
            for p in public["points"] if p.get("started_utc")] or [0]))})
    ET.SubElement(ET.SubElement(coverage, "sources"), "source").text = "."
    package = ET.SubElement(ET.SubElement(coverage, "packages"), "package", {"name": "DDTT",
        "line-rate": coverage.get("line-rate"), "branch-rate": "0", "complexity": "0"})
    classes = ET.SubElement(package, "classes")
    lcov = ["TN:DDTT_selected_assertions"]
    for name, lines in sorted(marks.items()):
        lcov += ["SF:" + name] + [f"DA:{line},{hit}" for line, hit in sorted(lines.items())]
        lcov += [f"LF:{len(lines)}", f"LH:{sum(lines.values())}", "end_of_record"]
        cls = ET.SubElement(classes, "class", {"name": name, "filename": name,
            "line-rate": str(sum(lines.values()) / len(lines)), "branch-rate": "0", "complexity": "0"})
        ET.SubElement(cls, "methods")
        entries = ET.SubElement(cls, "lines")
        for line, hit in sorted(lines.items()):
            ET.SubElement(entries, "line", {"number": str(line), "hits": str(hit), "branch": "false"})
    return "\n".join(lcov) + "\n", ET.tostring(coverage, encoding="unicode")


def render(public, sources):
    groups = defaultdict(list)
    for point in public["points"]:
        groups[(point["source"], point["line"])].append(point)
    sections, panels, options = [], [], []
    for index, (source, lines) in enumerate(sorted(sources.items())):
        options.append(f'<option value="file{index}">{escape(source)}</option>')
        rows = []
        for number, text in enumerate(lines, 1):
            points = groups[(source, number)]
            state, key = line_state(points), f"f{index}l{number}"
            title = f"{source}:{number} — {state}"
            rows.append(f'<button class="code-line {state}" data-key="{key}" title="{escape(title, quote=True)}">'
                        f'<span class="number">{number}</span><code>{escape(text) or " "}</code></button>')
            evidence = []
            for p in points:
                link = (f'<a href="{escape(p["scenario_url"], quote=True)}">{escape(p["scenario"])}</a>'
                        if p["scenario_url"] else escape(p["scenario"]))
                evidence.append(f'<article><strong class="{p["state"]}">{p["state"]}</strong><p>{escape(p["check"])}</p>'
                                f'<p>{link}</p><small>{p["checks_passed"]}/{p["checks_total"]} assertions · '
                                f'{escape(p["started_utc"] or "no evidence")}</small></article>')
            url = github(public["repository"], public["revision"], source, number)
            panels.append(f'<section id="{key}" hidden><h2>{escape(source)}:{number}</h2>'
                          f'<p><a href="{escape(url, quote=True)}">Открыть в GitHub ↗</a></p>'
                          + (''.join(evidence) or '<p>Нет привязки DDTT / unmapped. Это не FAIL.</p>') + '</section>')
        sections.append(f'<section class="source" id="file{index}"'+(' hidden' if index else '')+'>'+''.join(rows)+'</section>')
    css = Path(__file__).with_name("ddtt_pages.css").read_text(encoding="utf-8")
    theme = Path(__file__).with_name("ddtt_theme.js").read_text(encoding="utf-8")
    return ('<!doctype html><html lang="ru" data-theme="dark"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width"><title>DDTT — исходники и свидетельства</title>'
            '<style>'+css+'</style><body><header><h1>DDTT · исходники и свидетельства</h1>'
            '<p>Зелёный — подтверждены выбранные ожидания; красный — есть FAIL; жёлтый — есть UNKNOWN; '
            'без цвета — нет привязки. Это не процент исполнения прошивки. Нажмите строку для подробностей.</p>'
            '<p>Ревизия <a href="https://github.com/'+escape(public["repository"], quote=True)+'/tree/'+public["revision"]+'">'
            +public["revision"]+'</a> · '+escape(json.dumps(public["summary"]))+'</p>'
            '<p>Источник: '+escape(public['environment'])+' · '+str(public['campaign_attempts'])+' попыток в зафиксированной кампании.</p>'
            '<p><a href="public-data.json">Публичная сводка</a> · <a href="lcov.info">LCOV</a> · '
            '<a href="coverage.xml">Cobertura</a>. Только выбранные утверждения; UNKNOWN исключён из числового покрытия.</p>'
            '<p>Сценарии и исходники сверены с ревизией до/после кампании. Полные журналы и значения остаются локально.</p></header>'
            '<nav><label>Файл <select id="file">'+''.join(options)+'</select></label>'
            '<label><input id="mapped" type="checkbox"> Только строки с привязками</label>'
            '<button id="theme" aria-label="Тема">☾</button></nav><main><div id="sources">'+''.join(sections)+'</div>'
            '<aside><p id="hint">Выберите строку / Select a line</p>'+''.join(panels)+'</aside></main>'
            '<script>'+theme+'''
const select=document.getElementById('file'),mapped=document.getElementById('mapped');
function filter(){document.querySelectorAll('.source').forEach(s=>s.hidden=s.id!==select.value);
document.querySelectorAll('.code-line.UNMAPPED').forEach(s=>s.hidden=mapped.checked);}
select.addEventListener('change',filter);mapped.addEventListener('change',filter);
document.querySelectorAll('.code-line').forEach(button=>button.addEventListener('click',()=>{
document.querySelectorAll('aside section').forEach(s=>s.hidden=s.id!==button.dataset.key);
document.querySelectorAll('.code-line').forEach(s=>s.classList.toggle('selected',s===button));
document.getElementById('hint').hidden=true;}));filter();</script></body></html>''')

