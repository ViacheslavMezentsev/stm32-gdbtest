# record

[API](index.md) · [English](../../en/api/record.md)

`record(name, data) -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.2.0.dev0 → 0.2.0rc1 |
| Контракт принят в ТЗ API | 0.2.0; §4.9 |
| API_VERSION | 1 |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |

Новый пакет реализован; `0.2.0rc1` — локальный кандидат, не опубликованный стабильный релиз.

## Назначение

Добавляет глубокую копию data в журнал текущего вызова сценария. name — непустой точный str; имена могут повторяться.

## Контракт и ограничения

Допустимы точные None/bool/int, конечный float, Unicode str, list и dict со строковыми ключами. tuple, bytes, подклассы, объекты GDB, циклы, NaN/Inf запрещены. Отказ RecordError не расходует sequence/бюджет. Не читает MCU, не экспортирует и не меняет исход теста.

Лимиты задаются в `[records]` файла api.toml. Целые от 1 до максимума, не bool:

| Parameter | Default | Maximum |
| --- | ---: | ---: |
| max_records | 128 | 1024 |
| max_nodes | 4096 | 32768 |
| max_text_bytes | 65536 | 524288 |
| max_depth | 8 | 32 |
| max_integer_bits | 256 | 1024 |

Записи, узлы и UTF-8 байты ограничивают весь журнал. Глубина data начинается с 0;
integer_bits — int.bit_length. Узлы включают имена, ключи, значения и контейнеры;
байты — имена, ключи и строки. Служебная обёртка не учитывается. Это не лимит RSS
или количества копий, удерживаемых сценарием.

`t.record(name, t.profile)` записывает снимок профиля прогона (`profile.snapshot()`).

## Пример

```python
t.record("adc.sample", {"vdda_mv": t.value("board_adc_reading.vdda_mv")})
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.9.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/common/tests/board/test_measurements.py).
- [records](records.md), [record_error](record-error.md), [profile](profile.md).
