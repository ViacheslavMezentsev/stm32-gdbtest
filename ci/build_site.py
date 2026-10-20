"""Build the bilingual, dependency-free GitHub Pages site: skill routes and the API 3 reference.

Markup and site/assets follow the shared style of the STM32 project sites (demo-stm32-skills,
stm32-flasher): GitHub Primer colours, dark theme by default, round theme toggle, boxes,
stage/flow/node diagrams, cards and labels. Content lives in site/content.py.
"""

import argparse
import html
import keyword
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'site'))
import content  # noqa: E402

REPO = content.REPO
FAMILY = 'https://viacheslavmezentsev.github.io/demo-stm32-skills/'
VERSION = re.search(r'__version__ = "([^"]+)"', (ROOT / 'stm32_gdbtest/__init__.py').read_text(encoding='utf-8')).group(1)
API_VERSION = re.search(r'API_VERSION = (\d+)', (ROOT / 'stm32_gdbtest/__init__.py').read_text(encoding='utf-8')).group(1)

TEXT = {
    'ru': {
        'skip': 'К содержимому', 'sections': 'Разделы', 'routes': 'Маршруты', 'api': 'API', 'repo': 'Репозиторий',
        'intro': 'Сценарии в репозитории проекта проверяют работающую прошивку на реальной плате STM32 через GDB и '
                 'SWD-отладчик. Тестового кода в прошивке нет.',
        'release': 'Выпуск', 'sources': 'Исходники', 'docs': 'Документация', 'readme': 'README',
        'how': 'Как это работает', 'how_note': 'Host runner запускает GDB с Python-сценарием; Target API управляет '
               'остановками, читает данные и регистры, сохраняет свидетельства. Один сценарий запускается вручную, '
               'из CTest, в CI или в цикле на стенде.',
        'chain': [('offline', 'ELF + профиль', 'сценарии Python в проекте'), ('offline', 'Host runner', 'на ПК или в CI'),
                  ('live', 'GDB-Python', 'сценарий и Target API'), ('live', 'GDB-сервер', 'OpenOCD, ST-LINK, J-Link'),
                  ('live', 'STM32', 'прошивка приложения по SWD'), ('view', 'Отчёт', 'JSON, JUnit, журнал')],
        'parts': 'Разделы сайта',
        'routes_card': 'Как сочетать навыки агента: свидетели цели, правила TTDD, выбор навыка и семь типовых маршрутов.',
        'api_card': 'Методы Target API 3 по группам: сигнатуры, первый выпуск, изменения 0.5.0, примеры «правильно» '
                    'и «не рекомендуется».',
        'api3': 'API 3 кратко',
        'routes_title': 'Маршруты навыков', 'routes_lead': 'TTDD = DDTT + другие свидетели цели. Модуль отвечает за '
                        'проверку с остановками; навыки-спутники добавляют взгляд без остановки ядра, снаружи и без платы.',
        'witnesses': 'Свидетели цели', 'w_cols': ('Свидетель', 'Что показывает', 'Воздействие на цель', 'Навыки'),
        'rules': 'Правила', 'choose': 'Как выбирать навык', 'c_cols': ('Навык', 'Когда и что дать', 'Результат'),
        'routes_box': 'Типовые маршруты', 'alt': 'или', 'skills': 'Навыки модуля',
        'skills_note': 'Каждый навык — каталог с SKILL.md в формате Agent Skills; версия навыка совпадает с версией модуля.',
        'companions': 'Навыки-спутники', 'companions_note': 'Из demo-stm32-skills: требования, эмуляторы, '
                      'наблюдение без остановки ядра, сигналы на выводах.',
        'api_title': 'Справочник API', 'api_lead': f'Target API выпуска {VERSION}, API_VERSION={API_VERSION}. '
                     'Для каждой группы — сигнатуры, первый выпуск, изменения API 3 и примеры.',
        'groups': 'Группы методов', 'removed': 'Удалённые имена',
        'removed_note': 'Были доступны с 0.1.0-rc.1 по 0.3.0 (в 0.3.0 с предупреждением deprecated), удалены в 0.4.0.',
        'r_cols': ('Имя', 'Замена'), 'since': 'с', 'methods': 'Методы', 'm_cols': ('Элемент', 'Сигнатура', 'Доступен с', 'API 3'),
        'base_note': '¹ Базовая форма; расширения 0.3.0 описаны в карточке.',
        'changes': 'Изменения API 3 (0.5.0)', 'good': 'Правильно', 'bad': 'Не рекомендуется',
        'bad_note': 'Фрагменты показывают отклонённые или нежелательные приёмы, а не рабочий рецепт.',
        'cards': 'Карточки справочника', 'all': 'Все группы',
        'fragment': 'Фрагменты для тела сценария; символы прошивки условные.',
        'license': 'лицензия MIT', 'issue': 'Сообщить о проблеме', 'family': 'навыки demo-stm32-skills',
        'card_lang': 'ru', 'reference': 'Справочник в репозитории',
    },
    'en': {
        'skip': 'Skip to content', 'sections': 'Sections', 'routes': 'Routes', 'api': 'API', 'repo': 'Repository',
        'intro': 'Scenarios kept in the project repository check the running firmware on a real STM32 board through '
                 'GDB and an SWD debugger. There is no test code in the firmware.',
        'release': 'Release', 'sources': 'Sources', 'docs': 'Documentation', 'readme': 'README',
        'how': 'How it works', 'how_note': 'The host runner starts GDB with a Python scenario; the Target API controls '
               'stops, reads data and registers and keeps the evidence. One scenario runs by hand, from CTest, in CI '
               'or in a loop on a stand.',
        'chain': [('offline', 'ELF + profile', 'Python scenarios in the project'), ('offline', 'Host runner', 'on a PC or in CI'),
                  ('live', 'GDB-Python', 'scenario and Target API'), ('live', 'GDB server', 'OpenOCD, ST-LINK, J-Link'),
                  ('live', 'STM32', 'application firmware over SWD'), ('view', 'Report', 'JSON, JUnit, journal')],
        'parts': 'Site sections',
        'routes_card': 'How to combine agent skills: target witnesses, TTDD rules, choosing a skill and seven typical routes.',
        'api_card': 'Target API 3 methods by group: signatures, first release, 0.5.0 changes, "recommended" and '
                    '"avoid" examples.',
        'api3': 'API 3 in short',
        'routes_title': 'Skill routes', 'routes_lead': 'TTDD = DDTT + other witnesses of the target. The module covers '
                        'checks with stops; companion skills add views without halting the core, from outside and '
                        'without a board.',
        'witnesses': 'Target witnesses', 'w_cols': ('Witness', 'What it shows', 'Effect on the target', 'Skills'),
        'rules': 'Rules', 'choose': 'Choosing a skill', 'c_cols': ('Skill', 'When and what to supply', 'Result'),
        'routes_box': 'Typical routes', 'alt': 'or', 'skills': 'Module skills',
        'skills_note': 'Each skill is a directory with SKILL.md in the Agent Skills format; the skill version matches the module.',
        'companions': 'Companion skills', 'companions_note': 'From demo-stm32-skills: requirements, emulators, '
                      'observation without halting the core, signals on pins.',
        'api_title': 'API reference', 'api_lead': f'Target API of release {VERSION}, API_VERSION={API_VERSION}. '
                     'Each group gives signatures, the first release, API 3 changes and examples.',
        'groups': 'Method groups', 'removed': 'Removed names',
        'removed_note': 'Available from 0.1.0-rc.1 to 0.3.0 (with a deprecated warning in 0.3.0), removed in 0.4.0.',
        'r_cols': ('Name', 'Replacement'), 'since': 'since', 'methods': 'Methods',
        'm_cols': ('Entry', 'Signature', 'Available since', 'API 3'),
        'base_note': '¹ Base form; the 0.3.0 extensions are described in the card.',
        'changes': 'API 3 changes (0.5.0)', 'good': 'Recommended', 'bad': 'Avoid',
        'bad_note': 'The fragments show refused or discouraged patterns, not a working recipe.',
        'cards': 'Reference cards', 'all': 'All groups',
        'fragment': 'Fragments for a scenario body; firmware symbols are illustrative.',
        'license': 'MIT license', 'issue': 'Report an issue', 'family': 'demo-stm32-skills',
        'card_lang': 'en', 'reference': 'Reference in the repository',
    },
}

CHIP = ('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">'
        '<rect x="6" y="6" width="12" height="12" rx="1.5"/><rect x="9.5" y="9.5" width="5" height="5" rx="0.5"/>'
        '<path d="M9 2.5v3.5M12 2.5v3.5M15 2.5v3.5M9 18v3.5M12 18v3.5M15 18v3.5M2.5 9h3.5M2.5 12h3.5M2.5 15h3.5M18 9h3.5M18 12h3.5M18 15h3.5"/></svg>')

THEME_ICONS = (
    '<svg class="icon-dark" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M9.6 1.1a.75.75 0 0 1 .3.9 5.5 5.5 0 0 0 4.1 7.3.75.75 0 0 1 .4 1.3A7 7 0 1 1 8.3 1a.75.75 0 0 1 1.3.1ZM7.4 2.6a5.5 5.5 0 1 0 5.4 8.6 7 7 0 0 1-5.4-8.6Z"/></svg>'
    '<svg class="icon-light" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 11.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm0 1.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10ZM8 0a.75.75 0 0 1 .75.75v.5a.75.75 0 0 1-1.5 0v-.5A.75.75 0 0 1 8 0Zm0 14a.75.75 0 0 1 .75.75v.5a.75.75 0 0 1-1.5 0v-.5A.75.75 0 0 1 8 14ZM0 8a.75.75 0 0 1 .75-.75h.5a.75.75 0 0 1 0 1.5h-.5A.75.75 0 0 1 0 8Zm14 0a.75.75 0 0 1 .75-.75h.5a.75.75 0 0 1 0 1.5h-.5A.75.75 0 0 1 14 8ZM2.3 2.3a.75.75 0 0 1 1.06 0l.36.36a.75.75 0 0 1-1.06 1.06l-.36-.36a.75.75 0 0 1 0-1.06Zm9.98 9.98a.75.75 0 0 1 1.06 0l.36.36a.75.75 0 0 1-1.06 1.06l-.36-.36a.75.75 0 0 1 0-1.06ZM13.7 2.3a.75.75 0 0 1 0 1.06l-.36.36a.75.75 0 1 1-1.06-1.06l.36-.36a.75.75 0 0 1 1.06 0ZM3.72 12.28a.75.75 0 0 1 0 1.06l-.36.36a.75.75 0 0 1-1.06-1.06l.36-.36a.75.75 0 0 1 1.06 0Z"/></svg>'
    '<svg class="icon-auto" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0Zm0 1.5v13a6.5 6.5 0 0 0 0-13Z"/></svg>'
)

TOKEN = re.compile(r'(?P<c>#[^\n]*)|(?P<s>"""[\s\S]*?"""|"[^"\n]*"|\'[^\'\n]*\')|(?P<w>\b[A-Za-z_]\w*\b)')
KEYWORDS = set(keyword.kwlist)


def esc(value):
    return html.escape(value, quote=True)


def page_name(lang):
    return 'index.en.html' if lang == 'en' else 'index.html'


def code(source):
    """Python fragment with comment, string and keyword tokens (shared tok-* classes)."""
    parts, last = [], 0
    for match in TOKEN.finditer(source):
        parts.append(esc(source[last:match.start()]))
        text = esc(match.group())
        if match.lastgroup == 'c':
            parts.append(f'<span class="tok-c">{text}</span>')
        elif match.lastgroup == 's':
            parts.append(f'<span class="tok-s">{text}</span>')
        elif match.group() in KEYWORDS:
            parts.append(f'<span class="tok-k">{text}</span>')
        else:
            parts.append(text)
        last = match.end()
    parts.append(esc(source[last:]))
    return '<pre><code>' + ''.join(parts) + '</code></pre>'


def inline(text):
    """Plain text with `code` spans."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(text))


def shell(lang, title, description, body, depth, page):
    t = TEXT[lang]
    prefix = '../' * depth
    suffix = page_name(lang)
    current = {'routes': 'routes/', 'api': 'api/'}

    def nav(key):
        attr = ' aria-current="page"' if page == key else ''
        return f'<a href="{prefix}{current[key]}{suffix}"{attr}>{t[key]}</a>'

    ru_current = ' aria-current="page"' if lang == 'ru' else ''
    en_current = ' aria-current="page"' if lang == 'en' else ''
    return f'''<!doctype html>
<html lang="{lang}" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | stm32-gdbtest</title>
<meta name="description" content="{esc(description)}">
<link rel="stylesheet" href="{prefix}assets/site.css">
<script src="{prefix}assets/theme.js"></script>
</head>
<body>
<a class="skip" href="#main">{t['skip']}</a>
<header class="site-header">
  <div class="inner">
    <a class="brand" href="{prefix}{suffix}">{CHIP}<span>stm32-gdbtest</span></a>
    <nav class="site-nav" aria-label="{t['sections']}">
      {nav('routes')}
      {nav('api')}
      <a class="wide" href="{REPO}">{t['repo']}</a>
      <span class="lang-switch"><a href="index.html" lang="ru" hreflang="ru"{ru_current}>RU</a><a href="index.en.html" lang="en" hreflang="en"{en_current}>EN</a></span>
      <button id="theme-toggle" class="theme-toggle" type="button" aria-label="Theme">{THEME_ICONS}</button>
    </nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="inner">
    <span>stm32-gdbtest · {t['license']} · {VERSION} · API_VERSION={API_VERSION}</span>
    <a href="{REPO}">{t['sources']}</a>
    <a href="{REPO}/issues">{t['issue']}</a>
    <a href="{FAMILY}">{t['family']}</a>
  </div>
</footer>
</body>
</html>
'''


def crumb(lang, depth, *items):
    suffix = page_name(lang)
    parts = [f'<a href="{"../" * depth}{suffix}">stm32-gdbtest</a>']
    for href, label in items[:-1]:
        parts.append(f'<a href="{href}">{esc(label)}</a>')
    parts.append(esc(items[-1][1]))
    return '<div class="breadcrumb">' + ' / '.join(parts) + '</div>\n'


def table(head, rows):
    thead = ''.join(f'<th>{esc(cell)}</th>' for cell in head)
    return (f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def skill_node(key, lang, alt=False):
    s = content.SKILLS[key]
    prefix = f'{TEXT[lang]["alt"]}: ' if alt else ''
    return (f'<a class="node {s["kind"]}" href="{s["url"]}"><h3>{prefix}<code>{s["name"]}</code></h3>'
            f'<p>{esc(s[lang])}</p></a>')


def legend(lang):
    return '<div class="legend">' + ''.join(f'<span class="{c}">{esc(text)}</span>' for c, text in content.LEGEND[lang]) + '</div>'


def card_url(card, lang):
    return f'{REPO}/blob/main/docs/{TEXT[lang]["card_lang"]}/api/{card}.md'


def home_page(lang):
    t = TEXT[lang]
    suffix = page_name(lang)
    chips = ''.join(f'<span class="label">{x}</span>' for x in ('STM32', 'GDB-Python', 'SWD', 'OpenOCD · ST-LINK · J-Link', 'Renode · QEMU'))
    chips += f'<span class="label live">{VERSION}</span><span class="label alt">API_VERSION={API_VERSION}</span>'
    readme = 'README.en.md' if lang == 'en' else 'README.md'
    docs = f'docs/{lang}/index.md'
    chain = []
    for position, (kind, title, note) in enumerate(t['chain']):
        if position:
            chain.append('<div class="arrow"></div>')
        chain.append(f'<div class="node {kind}"><h3>{esc(title)}</h3><p>{esc(note)}</p></div>')
    body = f'<h1>stm32-gdbtest</h1>\n<p class="lead">{t["intro"]}</p>\n<div class="chips">{chips}</div>\n'
    body += (f'<div class="actions"><a class="btn primary" href="{REPO}/releases">{t["release"]} {VERSION}</a>'
             f'<a class="btn" href="{REPO}/blob/main/{readme}">{t["readme"]}</a>'
             f'<a class="btn" href="{REPO}/blob/main/{docs}">{t["docs"]}</a></div>\n')
    body += (f'<div class="box"><h2 id="how">{t["how"]}</h2><p>{t["how_note"]}</p>'
             f'<div class="flow">{"".join(chain)}</div></div>\n')
    body += (f'<div class="box"><h2 id="parts">{t["parts"]}</h2><div class="cards">'
             f'<a class="card" href="routes/{suffix}"><h3>{t["routes_title"]}</h3><p>{t["routes_card"]}</p>'
             f'<div class="meta"><span class="label offline">TTDD</span><span class="label live">DDTT</span></div></a>'
             f'<a class="card" href="api/{suffix}"><h3>{t["api_title"]}</h3><p>{t["api_card"]}</p>'
             f'<div class="meta"><span class="label alt">API_VERSION={API_VERSION}</span><span class="label">{len(content.API)}</span></div></a>'
             f'</div></div>\n')
    body += f'<div class="callout view"><h2 id="api3">{t["api3"]}</h2><p>{esc(content.API3_GENERAL[lang])}</p></div>'
    return shell(lang, 'stm32-gdbtest', t['intro'], body, 0, 'home')


def routes_page(lang):
    t = TEXT[lang]
    suffix = page_name(lang)
    index = 0 if lang == 'ru' else 1
    body = crumb(lang, 1, ('', t['routes']))
    body += f'<h1>{t["routes_title"]}</h1>\n<p class="lead">{t["routes_lead"]}</p>\n'
    rows = []
    for witness, shows, effect, skills in content.WITNESSES:
        links = ', '.join(f'<a href="{content.SKILLS[k]["url"]}"><code>{content.SKILLS[k]["name"]}</code></a>' for k in skills)
        rows.append((esc(witness[index]), esc(shows[index]), esc(effect[index]), links))
    body += f'<div class="box"><h2 id="witnesses">{t["witnesses"]}</h2>{table(t["w_cols"], rows)}</div>\n'
    facts = ''.join(f'<div class="fact"><b>{esc(b)}</b>{esc(text)}</div>' for b, text in content.RULES[lang])
    body += f'<div class="box"><h2 id="rules">{t["rules"]}</h2><div class="facts">{facts}</div></div>\n'
    rows = []
    for key, when_ru, result_ru, when_en, result_en in content.CHOOSE:
        s = content.SKILLS[key]
        name = f'<a href="{s["url"]}"><code>{s["name"]}</code></a>'
        rows.append((name, esc(when_ru if lang == 'ru' else when_en), esc(result_ru if lang == 'ru' else result_en)))
    body += f'<div class="box"><h2 id="choose">{t["choose"]}</h2>{table(t["c_cols"], rows)}</div>\n'
    stages = []
    for route in content.ROUTES:
        title, note = route[lang]
        nodes = []
        for position, key in enumerate(route['nodes']):
            if position:
                nodes.append('<div class="arrow"></div>')
            nodes.append(skill_node(key, lang))
        alt = ''.join(skill_node(key, lang, alt=True) for key in route.get('alt', ()))
        alt = f'<div class="alt-row"><div class="flow">{alt}</div></div>' if alt else ''
        stages.append(f'<div class="stage plain" id="{route["id"]}"><div class="stage-title">{esc(title)}</div>'
                      f'<div class="stage-note">{esc(note)}</div><div class="flow">{"".join(nodes)}</div>{alt}</div>')
    body += f'<div class="box"><h2 id="routes">{t["routes_box"]}</h2>{legend(lang)}{"".join(stages)}</div>\n'
    module = [k for k, s in content.SKILLS.items() if s['url'].startswith(REPO)]
    others = [k for k in content.SKILLS if k not in module]
    for anchor, title, note, keys in (('skills', t['skills'], t['skills_note'], module),
                                      ('companions', t['companions'], t['companions_note'], others)):
        cards = ''.join(f'<a class="card" href="{content.SKILLS[k]["url"]}"><h3><code>{content.SKILLS[k]["name"]}</code></h3>'
                        f'<p>{esc(content.SKILLS[k][lang])}</p><div class="meta"><span class="label {content.SKILLS[k]["kind"]}">'
                        f'{esc(dict(content.LEGEND[lang])[content.SKILLS[k]["kind"]])}</span></div></a>' for k in keys)
        body += f'<div class="box"><h2 id="{anchor}">{title}</h2><p class="muted">{note}</p><div class="cards">{cards}</div></div>\n'
    body += f'<div class="actions"><a class="btn primary" href="../api/{suffix}">{t["api_title"]} →</a></div>'
    return shell(lang, t['routes_title'], t['routes_lead'], body, 1, 'routes')


def since_labels(group):
    releases = []
    for _, since in group['methods']:
        if since not in releases:
            releases.append(since)
    return releases


def label_kind(release):
    return 'live' if release == '0.5.0' else 'offline'


def api_index(lang):
    t = TEXT[lang]
    suffix = page_name(lang)
    body = crumb(lang, 1, ('', t['api']))
    body += f'<h1>{t["api_title"]}</h1>\n<p class="lead">{t["api_lead"]}</p>\n'
    body += f'<div class="callout view"><h2 id="api3">{t["api3"]}</h2><p>{esc(content.API3_GENERAL[lang])}</p></div>\n'
    cards = []
    for group in content.API:
        meta = ''.join(f'<span class="label {label_kind(r)}">{t["since"]} {r}</span>' for r in since_labels(group))
        cards.append(f'<a class="card" href="{group["id"]}/{suffix}"><h3>{esc(group[lang]["title"])}</h3>'
                     f'<p>{esc(group[lang]["summary"])}</p><div class="meta">{meta}</div></a>')
    body += f'<div class="box"><h2 id="groups">{t["groups"]}</h2><div class="cards">{"".join(cards)}</div></div>\n'
    rows = [(f'<a href="{card_url(name, lang)}"><code>{name}</code></a>', f'<code>{esc(repl)}</code>') for name, repl in content.REMOVED]
    body += (f'<div class="box"><h2 id="removed">{t["removed"]}</h2><p>{t["removed_note"]}</p>'
             f'{table(t["r_cols"], rows)}</div>\n')
    body += (f'<div class="actions"><a class="btn" href="{REPO}/blob/main/docs/{lang}/api/index.md">{t["reference"]}</a>'
             f'<a class="btn" href="../routes/{suffix}">{t["routes_title"]}</a></div>')
    return shell(lang, t['api_title'], t['api_lead'], body, 1, 'api')


def group_page(position, lang):
    t = TEXT[lang]
    suffix = page_name(lang)
    group = content.API[position]
    d = group[lang]
    body = crumb(lang, 2, (f'../{suffix}', t['api']), ('', d['title']))
    body += f'<h1>{esc(d["title"])}</h1>\n<p class="lead">{esc(d["summary"])}</p>\n'
    body += '<div class="chips">' + ''.join(f'<span class="label {label_kind(r)}">{t["since"]} {r}</span>' for r in since_labels(group)) + '</div>\n'
    rows, base = [], False
    for card in group['cards']:
        sig, since, note_ru, note_en = content.CARDS[card]
        base = base or since.endswith('¹')
        name = content.CARD_NAMES.get(card, card)
        rows.append((f'<a href="{card_url(card, lang)}"><code>{esc(name)}</code></a>', f'<code>{esc(sig)}</code>',
                     esc(since), esc(note_ru if lang == 'ru' else note_en)))
    note = f'<p class="muted">{t["base_note"]}</p>' if base else ''
    body += f'<div class="box"><h2 id="methods">{t["methods"]}</h2>{table(t["m_cols"], rows)}{note}</div>\n'
    body += f'<div class="callout view"><h2 id="changes">{t["changes"]}</h2><p>{inline(d["api3"])}</p></div>\n'
    body += (''
             f'<div class="box"><h2 id="good"><span class="label live">{t["good"]}</span></h2><p>{inline(d["good"])}</p>{code(group["good"])}</div>'
             f'<div class="box"><h2 id="bad"><span class="label view">{t["bad"]}</span></h2><p>{inline(d["bad"])}</p>{code(group["bad"])}'
             f'<p class="muted">{t["bad_note"]}</p></div>\n')
    body += f'<p class="muted">{t["fragment"]}</p>\n'
    links = []
    if position:
        prev = content.API[position - 1]
        links.append(f'<a class="btn" href="../{prev["id"]}/{suffix}">← {esc(prev[lang]["title"].split(":")[0])}</a>')
    links.append(f'<a class="btn" href="../{suffix}#groups">{t["all"]}</a>')
    if position + 1 < len(content.API):
        nxt = content.API[position + 1]
        links.append(f'<a class="btn primary" href="../{nxt["id"]}/{suffix}">{esc(nxt[lang]["title"].split(":")[0])} →</a>')
    body += f'<div class="actions">{"".join(links)}</div>'
    return shell(lang, d['title'], d['summary'], body, 2, 'api')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def build(destination):
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'site/assets', destination / 'assets', dirs_exist_ok=True)
    for lang in TEXT:
        suffix = page_name(lang)
        write(destination / suffix, home_page(lang))
        write(destination / 'routes' / suffix, routes_page(lang))
        write(destination / 'api' / suffix, api_index(lang))
        for position, group in enumerate(content.API):
            write(destination / 'api' / group['id'] / suffix, group_page(position, lang))
    (destination / '.nojekyll').touch()
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output.resolve())
