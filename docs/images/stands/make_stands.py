"""Generate the schematic top views of the stand boards (docs/images/stands/*.svg).

One style and one scale for every board: 1 mm = SCALE px, so the relative sizes are real.
Positions are taken from top-view photos of the actual stands (orientation as photographed);
they are approximate (about 0.5 mm) and show only the parts that matter for a test stand:
MCU, connectors, buttons, LEDs, crystals, pin headers and the SWD header.

Run from the repository root: python docs/images/stands/make_stands.py
"""
from pathlib import Path

SCALE = 6
OUT = Path(__file__).resolve().parent
PAD = 4  # mm around the board for labels

COLORS = dict(
    black='#2b2f36', blue='#1f4f8f', white='#eef0f3', green='#2f6b3a',
    mcu='#15171a', pin='#c9a227', usb='#b8bcc4', button='#d9dce1', cap='#3a3d42',
    crystal='#cfd3d9', red='#e5484d', green_led='#3fb950', blue_led='#4f8fff', hole='#c9a227',
    lcd='#9fb8c8')


class Board:
    def __init__(self, name, title, width, height, pcb, text):
        self.name, self.title, self.w, self.h, self.pcb, self.text = name, title, width, height, pcb, text
        self.items = []

    def add(self, svg):
        self.items.append(svg)

    # Geometry helpers in millimetres.
    def rect(self, x, y, w, h, fill, stroke='none', rx=0.3, dash=None, width=0.25):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{width}"{d}/>')

    def label(self, x, y, text, size=1.9, anchor='middle', color=None, weight='normal'):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
                 f'fill="{color or self.text}">{text}</text>')

    def header(self, x0, y, count, pitch=2.54, rows=1):
        for row in range(rows):
            for n in range(count):
                self.add(f'<circle cx="{x0 + n * pitch:.2f}" cy="{y + row * pitch:.2f}" r="0.75" '
                         f'fill="none" stroke="{COLORS["pin"]}" stroke-width="0.45"/>')

    def vheader(self, x, y0, count, pitch=2.54, label=None):
        for n in range(count):
            self.add(f'<circle cx="{x}" cy="{y0 + n * pitch:.2f}" r="0.75" fill="none" '
                     f'stroke="{COLORS["pin"]}" stroke-width="0.45"/>')
        if label:
            mid = y0 + (count - 1) * pitch / 2
            self.add(f'<text x="{x + 2.0}" y="{mid}" font-size="1.6" text-anchor="middle" fill="{self.text}" '
                     f'transform="rotate(90 {x + 2.0} {mid})">{label}</text>')

    def mcu(self, cx, cy, size, text, rotate=0, leads=False, dash=False, ink=None):
        g = [f'<g transform="rotate({rotate} {cx} {cy})">']
        half = size / 2
        if leads:
            step = size / 13
            for side in range(4):
                for n in range(12):
                    t = -half + step * (n + 0.5) + step / 2
                    if side == 0:
                        g.append(f'<rect x="{cx + t - 0.12:.2f}" y="{cy - half - 0.9:.2f}" width="0.24" height="0.9" fill="#aab0b8"/>')
                    elif side == 1:
                        g.append(f'<rect x="{cx + t - 0.12:.2f}" y="{cy + half:.2f}" width="0.24" height="0.9" fill="#aab0b8"/>')
                    elif side == 2:
                        g.append(f'<rect x="{cx - half - 0.9:.2f}" y="{cy + t - 0.12:.2f}" width="0.9" height="0.24" fill="#aab0b8"/>')
                    else:
                        g.append(f'<rect x="{cx + half:.2f}" y="{cy + t - 0.12:.2f}" width="0.9" height="0.24" fill="#aab0b8"/>')
        style = f'fill="none" stroke="{ink or self.text}" stroke-width="0.35" stroke-dasharray="1 0.7"' if dash else \
            f'fill="{COLORS["mcu"]}" stroke="#555" stroke-width="0.2"'
        g.append(f'<rect x="{cx - half}" y="{cy - half}" width="{size}" height="{size}" rx="0.4" {style}/>')
        g.append(f'<circle cx="{cx - half + 0.9}" cy="{cy - half + 0.9}" r="0.35" fill="#666"/>' if not dash else '')
        g.append('</g>')
        self.add(''.join(g))
        for i, line in enumerate(text.split('\n')):
            self.label(cx, cy + 0.6 + (i - (text.count('\n')) / 2) * 2.0, line, size=1.6,
                       color='#ffffff' if not dash else (ink or self.text))

    def button(self, x, y, w, h, text, cap=COLORS['cap'], where='above'):
        self.rect(x, y, w, h, COLORS['button'], rx=0.4)
        self.add(f'<circle cx="{x + w / 2}" cy="{y + h / 2}" r="{min(w, h) * 0.3}" fill="{cap}"/>')
        if where == 'above':
            self.label(x + w / 2, y - 0.6, text)
        elif where == 'below':
            self.label(x + w / 2, y + h + 2.0, text)
        elif where == 'left':
            self.label(x - 0.6, y + h / 2 + 0.6, text, anchor='end')
        else:
            self.label(x + w + 0.6, y + h / 2 + 0.6, text, anchor='start')

    def led(self, x, y, color, text, where='left'):
        self.rect(x, y, 1.6, 0.9, color, rx=0.15)
        if where == 'left':
            self.label(x - 0.5, y + 0.8, text, anchor='end', size=1.7)
        elif where == 'right':
            self.label(x + 2.1, y + 0.8, text, anchor='start', size=1.7)
        elif where == 'above':
            self.label(x + 0.8, y - 0.5, text, size=1.7)
        else:
            self.label(x + 0.8, y + 2.6, text, size=1.7)

    def usb(self, x, y, w, h, text, where='right'):
        self.rect(x, y, w, h, COLORS['usb'], stroke='#7d828a', rx=0.8)
        if where == 'right':
            self.label(x + w + 0.6, y + h / 2 + 0.6, text, anchor='start', size=1.6)
        elif where == 'below':
            self.label(x + w / 2, y + h + 2.0, text, size=1.6)
        else:
            self.label(x + w / 2, y - 0.6, text, size=1.6)

    def crystal(self, x, y, w, h, text=None):
        self.rect(x, y, w, h, COLORS['crystal'], stroke='#8a9099', rx=0.4)
        if text:
            self.label(x + w / 2, y - 0.5, text, size=1.5)

    def hole(self, cx, cy, r=1.6):
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{COLORS["hole"]}" stroke-width="0.6"/>')

    def svg(self):
        w, h = self.w + 2 * PAD, self.h + 2 * PAD + 6
        body = '\n'.join(self.items)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * SCALE:.0f}" height="{h * SCALE:.0f}" '
                f'viewBox="{-PAD} {-PAD - 6} {w} {h}" font-family="Segoe UI, Arial, sans-serif">\n'
                f'<title>{self.title}</title>\n'
                f'<rect x="{-PAD}" y="{-PAD - 6}" width="{w}" height="{h}" fill="#ffffff"/>\n'
                f'<text x="0" y="-5.4" font-size="2.2" font-weight="bold" fill="#24292f">{self.title}</text>\n'
                f'<text x="0" y="-2.4" font-size="1.8" fill="#57606a">'
                f'≈ {self.w:g} × {self.h:g} мм, вид сверху</text>\n'
                f'<rect x="0" y="0" width="{self.w}" height="{self.h}" rx="1.2" fill="{self.pcb}" '
                f'stroke="#1b1f24" stroke-width="0.3"/>\n{body}\n</svg>\n')


def weact_pill(name, title, pcb, mcu, rotate, leads, led_text, key_text, w=52.8, h=20.8):
    """WeAct BlackPill / BluePill-Plus / AT32 core board: same footprint and layout."""
    b = Board(name, title, w, h, pcb, '#e6edf3')
    b.header(1.1, 2.6, 20)
    b.header(1.1, h - 2.6, 20)
    b.usb(-0.6, 5.6, 7.6, 9.4, '')
    b.label(3.2, 17.0, 'USB-C', size=1.5)
    b.button(12.4, 6.0, 5.6, 3.4, 'NRST')
    b.button(12.4, 11.0, 5.6, 3.4, 'BOOT0', where='below')
    b.mcu(26.4, 10.4, 7.0, mcu, rotate=rotate, leads=leads)
    b.crystal(34.2, 6.2, 2.7, 3.1)
    b.crystal(34.4, 10.6, 1.9, 3.0)
    b.led(40.8, 5.0, COLORS['blue_led'], led_text)
    b.button(38.4, 10.6, 5.4, 3.6, key_text, where='above')
    b.led(40.8, 15.0, COLORS['red'], 'PWR')
    b.vheader(46.2, 5.4, 4, label='SWD')
    return b


def boards():
    yield weact_pill('weact-at32f403a', 'WeAct AT32F403A V1.0 (AT32F403ACGU7)', COLORS['black'],
                     'AT32F403A\nQFN48', 45, False, 'C13', 'KEY', w=52.2, h=21.2)
    yield weact_pill('weact-bluepill-plus-f103cb', 'WeAct BluePill-Plus (STM32F103CBT6)', COLORS['blue'],
                     'F103CBT6\nLQFP48', 45, True, 'PB2', 'KEY', w=53.3, h=20.9)
    yield weact_pill('weact-blackpill-f411ce', 'WeAct BlackPill V2/V3 (STM32F411CEU6)', COLORS['black'],
                     'F411CEU6\nQFN48', 45, False, 'C13', 'KEY', w=52.8, h=20.8)

    # WeAct MiniF4 early revision with micro-USB, UKEY and four mounting holes (STM32F401CCU6).
    b = Board('weact-minif4-f401cc', 'WeAct MiniF4 (STM32F401CCU6), ранняя ревизия', 63.4, 25.0,
              COLORS['black'], '#e6edf3')
    for x, y in ((2.3, 2.3), (61.1, 2.3), (2.3, 22.7), (61.1, 22.7)):
        b.hole(x, y)
    b.header(7.7, 2.8, 20)
    b.header(7.7, 21.4, 20)
    b.usb(-1.0, 8.0, 6.6, 6.9, '', where='below')
    b.label(0.8, 17.4, 'micro-USB', size=1.5, anchor='start')
    b.button(14.0, 9.0, 2.8, 5.9, 'UKEY', where='above')
    b.button(20.1, 8.0, 5.2, 2.2, 'RST', where='above')
    b.button(20.1, 13.4, 5.2, 2.2, 'BOOT0', where='below')
    b.mcu(38.1, 12.4, 7.0, 'F401CCU6\nQFN48', rotate=45)
    b.crystal(48.0, 7.7, 2.8, 2.4)
    b.crystal(48.8, 12.6, 2.0, 3.6)
    b.led(57.6, 7.5, COLORS['red'], 'D2', where='left')
    b.led(57.6, 13.6, COLORS['blue_led'], 'D3', where='left')
    yield b

    # NUCLEO-F030R8 (MB1136), photographed with the ST-LINK part on the left.
    b = Board('nucleo-f030r8', 'ST NUCLEO-F030R8 (MB1136, STM32F030R8T6)', 82.5, 70.0, COLORS['white'], '#24292f')
    b.add('<line x1="29.3" y1="1" x2="29.3" y2="69" stroke="#9aa3ad" stroke-width="0.35" stroke-dasharray="1.5 1"/>')
    b.label(14.5, 66.0, 'ST-LINK/V2-1', size=2.0, weight='bold')
    b.usb(-1.0, 18.3, 7.3, 6.7, '', where='above')
    b.label(0.6, 27.6, 'CN1 USB Mini-B', size=1.6, anchor='start')
    b.led(9.3, 8.4, COLORS['red'], 'LD1 COM', where='right')
    b.mcu(21.1, 31.5, 9.6, 'ST-LINK\nMCU', leads=True)
    b.crystal(15.5, 46.0, 6.0, 2.4, 'X1')
    b.header(13.3, 58.6, 6)
    b.label(19.6, 56.6, 'CN4 SWD', size=1.6)
    b.button(30.3, 21.3, 6.0, 6.7, 'B2 RESET')
    b.button(29.3, 36.3, 6.0, 7.0, 'B1 USER', cap='#2f6fd6', where='below')
    b.led(46.3, 24.3, COLORS['green_led'], 'LD2 (PA5)', where='right')
    b.led(47.2, 44.8, COLORS['red'], 'LD3 PWR', where='right')
    b.mcu(60.0, 35.0, 10.0, 'STM32F030\nR8T6\nLQFP64', leads=True)
    b.crystal(72.6, 48.0, 3.6, 5.4, 'X2 LSE')
    b.rect(71.6, 27.5, 5.4, 7.0, 'none', stroke='#9aa3ad', dash='0.8 0.6')
    b.label(74.3, 26.6, 'X3 (нет)', size=1.5)
    b.header(34.3, 1.6, 19, rows=2)
    b.label(33.0, 3.4, 'CN10', size=1.5, anchor='end')
    b.header(34.3, 65.4, 19, rows=1)
    b.header(34.3, 67.9, 19, rows=1)
    b.label(33.0, 67.2, 'CN7', size=1.5, anchor='end')
    b.rect(34.5, 8.6, 25.0, 2.6, 'none', stroke='#57606a')
    b.rect(61.0, 8.6, 20.0, 2.6, 'none', stroke='#57606a')
    b.rect(43.0, 55.7, 18.0, 2.6, 'none', stroke='#57606a')
    b.rect(65.6, 55.7, 15.2, 2.6, 'none', stroke='#57606a')
    b.label(58.0, 13.6, 'Arduino Uno V3 / morpho', size=1.6)
    yield b

    # STM32F429I-DISCO (MB1075B), LCD on the left, ST-LINK on the right.
    b = Board('stm32f429i-disco', 'ST STM32F429I-DISCO (MB1075B, STM32F429ZIT6)', 119.0, 66.0,
              COLORS['green'], '#e6edf3')
    b.header(6.6, 5.2, 32, rows=2)
    b.label(46.0, 2.8, 'P1', size=1.6)
    b.header(6.6, 55.2, 32, rows=2)
    b.label(46.0, 62.6, 'P2', size=1.6)
    b.rect(6.2, 10.4, 58.2, 41.7, '#c9ccd1', stroke='#7d828a', rx=0.6)
    b.rect(8.5, 13.0, 49.5, 36.5, COLORS['lcd'], rx=0.3)
    b.label(33.2, 31.5, 'LCD 2.4" QVGA (сенсорный)', size=2.4, color='#24292f')
    b.mcu(33.2, 40.0, 10.0, 'STM32F429ZIT6\n(на обороте)', dash=True, ink='#24292f')
    b.usb(-1.0, 27.5, 4.8, 3.8, '', where='below')
    b.label(0.6, 25.8, 'USB OTG', size=1.5, anchor='start')
    b.led(73.5, 13.8, COLORS['green_led'], 'LD3 PG13', where='left')
    b.led(73.5, 16.2, COLORS['red'], 'LD4 PG14', where='left')
    b.button(79.6, 14.7, 6.7, 10.9, 'B1 USER', cap='#2f6fd6', where='right')
    b.button(79.6, 37.9, 6.7, 10.4, 'B2 RESET', where='right')
    b.crystal(68.0, 33.0, 5.0, 8.5, 'X3')
    b.mcu(98.5, 28.9, 8.0, 'ST-LINK\nMCU', leads=True)
    b.crystal(96.0, 19.8, 6.0, 2.4)
    b.usb(110.0, 26.5, 10.0, 6.7, '', where='below')
    b.label(118.0, 36.4, 'CN1 USB Mini-B', size=1.6, anchor='end')
    b.led(109.2, 12.0, COLORS['red'], 'LD1 COM', where='left')
    b.led(109.2, 16.0, COLORS['red'], 'LD2 PWR', where='left')
    b.header(92.4, 3.8, 6)
    b.label(98.8, 1.8, 'CN2 SWD', size=1.6)
    b.label(98.0, 62.0, 'ST-LINK/V2', size=2.0, weight='bold')
    yield b


def main():
    for b in boards():
        (OUT / f'{b.name}.svg').write_text(b.svg(), encoding='utf-8')
        print(b.name)


if __name__ == '__main__':
    main()
