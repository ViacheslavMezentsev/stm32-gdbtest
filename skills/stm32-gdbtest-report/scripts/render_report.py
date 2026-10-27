"""Две формы PDF из явного набора данных; без доступа к стенду или API ядра."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def validate(data):
    """Не принимать отсутствующие обязательные поля за пустое измерение."""
    for key in ('title', 'release', 'period', 'location', 'scope', 'recovery'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f'required text: {key}')
    if type(data.get('demonstration')) is not bool:
        raise ValueError('demonstration must be explicit')
    if not data.get('methods') or not data.get('evidence') or not data.get('excluded'):
        raise ValueError('methods, evidence and excluded are required')
    for item in data['methods']:
        for key in ('name', 'description', 'accuracy'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'method needs {key}')
    for item in data['evidence']:
        for key in ('title', 'requirement', 'scenario', 'conditions', 'conclusion', 'remarks', 'source'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'evidence needs {key}')
        if item.get('status') not in ('PASS', 'FAIL', 'ERROR', 'SKIP', 'UNKNOWN'):
            raise ValueError('unknown evidence status')
        if not item.get('columns') or not item.get('rows'):
            raise ValueError('table is required')
        if any(len(row) != len(item['columns']) for row in item['rows']):
            raise ValueError('inconsistent table width')
        chart = item.get('chart')
        if chart:
            import math
            if not chart.get('x_label') or not chart.get('y_label'):
                raise ValueError('chart needs labelled axes with units')
            a, b = chart['expected'], chart['observed']
            if len(a) < 2 or len(a) != len(b):
                raise ValueError('incomplete chart')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in a + b):
                raise ValueError('chart contains unknown/nonfinite values')


def render(data, destination, technical):
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'Body'
    styles.add(ParagraphStyle('TextRu', fontName='Body', fontSize=9.5, leading=13, spaceAfter=6))
    styles['Title'].fontName = styles['Heading1'].fontName = 'Bold'
    story = []

    def paragraph(value, style='TextRu'):
        return Paragraph(escape(str(value)), styles[style])

    def add(value, style='TextRu'):
        story.append(paragraph(value, style))

    def table(rows):
        width = 174 * mm / len(rows[0])
        value = Table([[paragraph(cell) for cell in row] for row in rows],
                      colWidths=[width] * len(rows[0]), repeatRows=1, hAlign='LEFT')
        value.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eef5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#ccd5df')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.extend([value, Spacer(1, 4 * mm)])

    add(data['title'], 'Title')
    add('Технический отчёт' if technical else 'Компактный обзор проверок', 'Heading1')
    if data['demonstration']:
        add('ДЕМОНСТРАЦИЯ — условные данные, не результат испытаний.')
    add(f"Объект: {data['release']}. Место: {data['location']}. Время: {data['period']}.")
    add(data['scope'])
    if technical:
        add('1. Как читать отчёт', 'Heading1')
        add('Требование → сценарий → измерения → график → вывод. Исход сценария, '
            'применимость и восстановление оцениваются отдельно. UNKNOWN не означает ноль.')
        add('2. Способы съёма и их точность', 'Heading1')
        table([['Способ', 'Что снимается', 'Точность и ограничения']] +
              [[m['name'], m['description'], m['accuracy']] for m in data['methods']])
        add('3. Перечень свидетельств', 'Heading1')
        table([['Свидетельство', 'Требование', 'Сценарий']] +
              [[e['title'], e['requirement'], e['scenario']] for e in data['evidence']])
    for number, item in enumerate(data['evidence'], 4):
        if technical:
            story.append(CondPageBreak(100 * mm))
        add(f"{number}. {item['title']}" if technical else item['title'], 'Heading1')
        add(f"Сценарий: {item['scenario']}. Исход: {item['status']}.")
        if technical:
            add('Требование: ' + item['requirement'])
            add('Условия и способ: ' + item['conditions'])
            table([item['columns']] + item['rows'])
            if item.get('chart'):
                chart = item['chart']
                drawing = Drawing(480, 225)
                plot = LinePlot()
                plot.x, plot.y, plot.width, plot.height = 48, 45, 390, 145
                plot.xValueAxis.valueStep = 1
                plot.data = [list(enumerate(chart[k])) for k in ('expected', 'observed')]
                plot.lines[0].strokeColor = colors.HexColor('#1767b0')
                plot.lines[0].strokeWidth = 3
                plot.lines[1].strokeColor = colors.HexColor('#cc6700')
                plot.lines[1].strokeDashArray = [4, 3]
                plot.xValueAxis.labels.fontName = plot.yValueAxis.labels.fontName = 'Body'
                drawing.add(plot)
                for x, y, text in ((48, 210, chart['y_label']), (180, 22, chart['x_label']),
                                   (48, 5, 'Синий — ожидание; оранжевый пунктир — наблюдение')):
                    drawing.add(String(x, y, text, fontName='Body', fontSize=9))
                story.append(drawing)
        add('Вывод: ' + item['conclusion'])
        add('Замечания: ' + item['remarks'])
    if technical:
        add('Сводка замечаний', 'Heading1')
        for item in data['evidence']:
            add(item['title'] + ': ' + item['remarks'])
    add('Что не вошло', 'Heading1')
    for value in data['excluded']:
        add(value)
    add('Восстановление: ' + data['recovery'])
    if technical:
        add('Приложение A. Происхождение данных', 'Heading1')
        for item in data['evidence']:
            add(item['title'] + ': ' + item['source'])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Body', 8)
        canvas.drawString(18 * mm, 12 * mm, 'DDTT — демонстрация' if data['demonstration'] else 'DDTT')
        canvas.drawRightString(192 * mm, 12 * mm, f'Стр. {doc.page}')
        canvas.restoreState()

    SimpleDocTemplate(str(destination), pagesize=(210 * mm, 297 * mm),
                      leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                      bottomMargin=22 * mm, title=data['title'], author='').build(
                          story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--font', type=Path, required=True)
    parser.add_argument('--font-bold', type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = json.loads(raw)
    validate(data)
    pdfmetrics.registerFont(TTFont('Body', str(args.font)))
    pdfmetrics.registerFont(TTFont('Bold', str(args.font_bold)))
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ('compact', 'technical'):
        render(data, args.output / (name + '.pdf'), name == 'technical')
    hashes = {'input_sha256': hashlib.sha256(raw).hexdigest(),
              'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'demonstration': data['demonstration']}
    (args.output / 'provenance.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
