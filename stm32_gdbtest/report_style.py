"""Shared light/dark palette for the standalone campaign report."""

CSS = """
:root{color-scheme:dark;--bg:#0d1117;--panel:#161b22;--panel2:#1c2128;--border:#30363d;
--fg:#e6edf3;--dim:#8b949e;--accent:#2f81f7;--pass:#3fb950;--fail:#f85149;--warn:#d29922}
@media(prefers-color-scheme:light){:root:not([data-theme=dark]){color-scheme:light;--bg:#f6f8fa;
--panel:#fff;--panel2:#f6f8fa;--border:#d0d7de;--fg:#1f2328;--dim:#59636e;
--accent:#0969da;--pass:#1a7f37;--fail:#cf222e;--warn:#9a6700}}
:root[data-theme=light]{color-scheme:light;--bg:#f6f8fa;--panel:#fff;--panel2:#f6f8fa;
--border:#d0d7de;--fg:#1f2328;--dim:#59636e;--accent:#0969da;--pass:#1a7f37;--fail:#cf222e;--warn:#9a6700}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
header{padding:14px 24px;background:var(--panel);border-bottom:1px solid var(--border)}
main{max-width:1560px;margin:auto;padding:24px}h1{font-size:26px;margin:0}h2{font-size:19px;margin:28px 0 12px}
.hero{background:var(--panel);padding:20px;border:1px solid var(--border);border-radius:8px}
.muted,small{color:var(--dim)}small{display:block;overflow-wrap:anywhere}p{margin:8px 0}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}.card{padding:10px 14px;background:var(--panel);
border:1px solid var(--border);border-radius:6px;min-width:105px}.card strong{display:block;font-size:23px}
.scroll{overflow-x:auto;border:1px solid var(--border);border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:1100px;background:var(--panel)}
th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--border);padding:12px}
th{background:var(--panel2);font-size:12px}td{max-width:320px;overflow-wrap:anywhere}
.PASS{color:var(--pass);font-weight:600}.FAIL,.ERROR,.issues{color:var(--fail);font-weight:600}
.SKIP,.unverified{color:var(--warn)}.UNKNOWN{color:var(--dim)}.ok{color:var(--pass)}
summary{cursor:pointer;color:var(--accent)}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;
max-width:430px;max-height:440px;overflow:auto;background:var(--panel2);padding:12px;border-radius:6px}
.note{border-left:3px solid var(--accent);padding:4px 12px;margin:16px 0}
footer{padding:24px;color:var(--dim);text-align:center;font-size:12px}
@media(max-width:700px){main{padding:12px}.hero{padding:14px}h1{font-size:22px}}
"""


CSS += """
.toolbar{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.toolbar[hidden]{display:none}.toolbar fieldset{border:0;padding:0;margin:0}
.toolbar legend{font-size:12px;color:var(--dim);margin-bottom:4px}
.toolbar button{font:inherit;color:var(--fg);background:var(--panel);border:1px solid var(--border);
padding:6px 12px;cursor:pointer;border-radius:5px;margin:2px}
.toolbar button[aria-pressed=true]{background:var(--accent);color:#fff;border-color:var(--accent)}
.toolbar button:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
:root[data-view=normal] .expert{display:none}
:root[data-view=normal] table{min-width:800px}
"""

CONTROLS = '''
<div class="toolbar" hidden>
<fieldset><legend>Тема / Theme</legend>
<button type="button" data-theme-choice="auto">Системная / Auto</button>
<button type="button" data-theme-choice="light">Светлая / Light</button>
<button type="button" data-theme-choice="dark">Тёмная / Dark</button></fieldset>
<fieldset><legend>Режим / View</legend>
<button type="button" data-view-choice="normal">Обычный / Normal</button>
<button type="button" data-view-choice="expert">Экспертный / Expert</button></fieldset>
</div>
<noscript><p class="muted">JavaScript отключён: показаны все подробности в исходной теме.
JavaScript disabled: all details shown in the initial theme.</p></noscript>
'''

# Static script only: evidence text is never interpolated into executable code.
SCRIPT = '''
(() => {
  const root = document.documentElement;
  function select(kind, value) {
    root.dataset[kind] = value;
    document.querySelectorAll('[data-' + kind + '-choice]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset[kind + 'Choice'] === value));
    });
  }
  for (const kind of ['theme', 'view']) {
    document.querySelectorAll('[data-' + kind + '-choice]').forEach(button => {
      button.addEventListener('click', () => select(kind, button.dataset[kind + 'Choice']));
    });
  }
  select('theme', root.dataset.theme);
  select('view', 'normal');
  document.querySelector('.toolbar').hidden = false;
})();
'''
