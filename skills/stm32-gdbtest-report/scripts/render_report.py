"""Две формы PDF из явного набора данных; без доступа к стенду или API ядра."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
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
            if chart.get('kind', 'line') not in ('line', 'bar'):
                raise ValueError('unsupported chart kind')
            a, b = chart['expected'], chart['observed']
            if 'labels' in chart and len(chart['labels']) != len(a):
                raise ValueError('chart labels do not match observations')
            if len(a) < 2 or len(a) != len(b):
                raise ValueError('incomplete chart')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in a + b):
                raise ValueError('chart contains unknown/nonfinite values')


def render(data, destination, technical):
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'Body'
    styles.add(ParagraphStyle('TextRu', fontName='Body', fontSize=9, leading=12, spaceAfter=5))
    styles['Title'].fontName = styles['Heading1'].fontName = 'Bold'
    blue = colors.HexColor('#1F4E79')
    styles['Title'].textColor = styles['Heading1'].textColor = blue
    styles['Title'].fontSize, styles['Title'].leading = 22, 27
    styles['Heading1'].fontSize, styles['Heading1'].leading = 13, 17
    styles['Heading1'].spaceBefore, styles['Heading1'].spaceAfter = 12, 7
    styles.add(ParagraphStyle('Cell', fontName='Body', fontSize=8, leading=10.5))
    styles.add(ParagraphStyle('CellHead', fontName='Bold', fontSize=8, leading=10.5, textColor=colors.white))
    styles.add(ParagraphStyle('Source', fontName='Body', fontSize=7.5, leading=10, textColor=colors.HexColor('#526477'), spaceAfter=6))
    story = []

    def paragraph(value, style='TextRu'):
        return Paragraph(escape(str(value)), styles[style])

    def add(value, style='TextRu'):
        story.append(paragraph(value, style))

    def table(rows):
        width = 174 * mm / len(rows[0])
        value = Table([[paragraph(cell, 'CellHead' if i == 0 else 'Cell') for cell in row] for i, row in enumerate(rows)],
                      colWidths=[width] * len(rows[0]), repeatRows=1, hAlign='LEFT')
        value.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), blue),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#EFF4F9'), colors.white]),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#ccd5df')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.extend([value, Spacer(1, 4 * mm)])

    def box(text, warning=False):
        value = Table([[paragraph(text)]], colWidths=[174 * mm])
        value.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF0E4' if warning else '#EAF1F9')),
            ('LINEBEFORE', (0, 0), (0, -1), 3, colors.HexColor('#DA7A29') if warning else blue),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.extend([value, Spacer(1, 3 * mm)])

    add('DDTT / СВИДЕТЕЛЬСТВА ПРОВЕРОК', 'Source')
    add(data['title'], 'Title')
    add('Технический отчёт' if technical else 'Компактный обзор проверок', 'Heading1')
    if data['demonstration']:
        add('ДЕМОНСТРАЦИЯ — условные данные, не результат испытаний.')
    add(f"Объект: {data['release']}. Место: {data['location']}. Время: {data['period']}.")
    box(data['scope'])
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
    if not technical:
        add('Объекты и результаты', 'Heading1')
        table([['Объект проверки', 'Наблюдение']] +
              [[item['title'], item['conclusion']] for item in data['evidence']])
    for number, item in enumerate(data['evidence'], 4):
        if technical:
            story.append(CondPageBreak(100 * mm))
        add(f"{number}. {item['title']}" if technical else item['title'], 'Heading1')
        add(f"Сценарий: {item['scenario']}. Исход: {item.get('status_label', item['status'])}.")
        if technical:
            box('Требование: ' + item['requirement'])
            add('Условия и способ: ' + item['conditions'])
            table([item['columns']] + item['rows'])
            if item.get('chart'):
                chart = item['chart']
                drawing = Drawing(480, 225)
                bars = chart.get('kind') == 'bar'
                plot = VerticalBarChart() if bars else LinePlot()
                plot.x, plot.y, plot.width, plot.height = 48, 50, 390, 140
                if bars:
                    plot.data = [chart[k] for k in ('expected', 'observed')]
                    plot.categoryAxis.categoryNames = chart.get('labels', [str(i) for i in range(len(chart['expected']))])
                    plot.categoryAxis.labels.fontName = 'Body'
                    plot.categoryAxis.labels.fontSize = 8
                    plot.valueAxis.labels.fontName = 'Body'
                    plot.valueAxis.valueMin = 0
                    plot.bars[0].fillColor = colors.HexColor('#2A6FDB')
                    plot.bars[1].fillColor = colors.HexColor('#E8692E')
                else:
                    plot.xValueAxis.valueStep = 1
                    plot.data = [list(enumerate(chart[k])) for k in ('expected', 'observed')]
                    plot.lines[0].strokeColor = colors.HexColor('#2A6FDB')
                    plot.lines[0].strokeWidth = 3
                    plot.lines[1].strokeColor = colors.HexColor('#E8692E')
                    plot.lines[1].strokeDashArray = [4, 3]
                    plot.xValueAxis.labels.fontName = plot.yValueAxis.labels.fontName = 'Body'
                drawing.add(plot)
                for x, y, text in ((48, 210, chart['y_label']), (170, 23, chart['x_label']),
                                   (48, 5, 'Синий — ожидание; оранжевый — наблюдение')):
                    drawing.add(String(x, y, text, fontName='Body', fontSize=8))
                story.append(drawing)
        add('Вывод: ' + item['conclusion'])
        box('Замечания: ' + item['remarks'], warning=True)
        if technical:
            add('Данные: ' + item['source'], 'Source')
    if technical:
        add('Сводка замечаний', 'Heading1')
        for item in data['evidence']:
            add(item['title'] + ': ' + item['remarks'])
    add('Что не вошло', 'Heading1')
    for value in data['excluded']:
        add(value)
    add('Восстановление: ' + data['recovery'])
    if technical:
        story.append(CondPageBreak(65 * mm))
        add('Приложение A. Происхождение данных', 'Heading1')
        for item in data['evidence']:
            story.append(CondPageBreak(40 * mm))
            add(item['title'] + ': ' + item['source'], 'Source')
            if item.get('provenance'):
                table([['Источник (роль)', 'SHA-256, начало']] +
                      [[p['label'], p['sha256'][:16]] for p in item['provenance']])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#9DB3CC'))
        canvas.line(18 * mm, 21 * mm, 192 * mm, 21 * mm)
        caption = data.get('footer', data['title'] + ', ' + data['release'] + ', ' + data['period'])
        foot = paragraph(caption, 'Source')
        _, height = foot.wrap(150 * mm, 16 * mm)
        if height > 16 * mm:
            raise ValueError('footer exceeds reserved area; shorten the object label')
        foot.drawOn(canvas, 18 * mm, 19 * mm - height)
        canvas.setFont('Body', 8)
        canvas.setFillColor(blue)
        canvas.drawRightString(192 * mm, 12 * mm, f'Стр. {doc.page}')
        canvas.restoreState()

    SimpleDocTemplate(str(destination), pagesize=(210 * mm, 297 * mm),
                      leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                      bottomMargin=28 * mm, title=data['title'], author='').build(
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
