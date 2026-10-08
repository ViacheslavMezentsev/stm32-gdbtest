# records

[API](index.md) · [English](../../en/api/records.md)

`records(name=None) -> list[dict]`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.2.0.dev0 → 0.2.0rc1 |
| Контракт принят в ТЗ API | 0.2.0; §4.10 |
| API_VERSION | 1 |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |

Новый пакет реализован; `0.2.0rc1` — локальный кандидат, не опубликованный стабильный релиз.

## Назначение

Возвращает независимые изменяемые копии записей sequence/name/data. None выбирает всё; непустой str — точное имя; отсутствие совпадений даёт [].

## Контракт и ограничения

Порядок вставки и sequence от 1 сохраняются после фильтрации. Изменение копий не меняет журнал. clear/reset/continue не очищают журнал текущего вызова. Неверный фильтр даёт RecordError. Каждый вызов копирует выборку.

## Пример

```python
from statistics import mean, stdev

samples = [row["data"]["vdda_mv"] for row in t.records("adc.sample")]
t.check("enough samples", len(samples) >= 2, True)
summary = {"mean": mean(samples), "stdev": stdev(samples)}
last_two = samples[-2:]
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

Пример требует не менее двух ранее накопленных adc.sample; stdev использует N−1.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.10.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/common/tests/board/test_measurements.py).
- [record](record.md), [record_error](record-error.md).

Opt-in сохранение runner: [описание](../API.md#захват-журнала-результатов-unreleased). Контракт метода не меняется.

Данные записей произвольны; name не определяет тип измерения. [Общий экспорт и отдельные проекции](../RESULTS.md).
