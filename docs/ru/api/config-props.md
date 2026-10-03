# config_props

[API](index.md) · [English](../../en/api/config-props.md)

`config_props: Mapping`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.2.0.dev0 → 0.2.0rc1 |
| Контракт принят в ТЗ API | 0.2.0; §4.12 |
| API_VERSION | 1 |

Новый пакет реализован; `0.2.0rc1` — локальный кандидат, не опубликованный стабильный релиз.

## Контракт

Глубоко неизменяемое отображение тех же ролей api/target/image. Для файла: data без defaults, sha256 исходных байтов и reference; для отсутствующего файла None.

Описывает тот же снимок, что config. Комментариев TOML в data нет. reference не гарантирует доступность пути на другом хосте; не открывайте его для получения фактической конфигурации запуска.

## Пример

```python
source = target.config_props["api"]
if source is not None:
    target.record("config.api", {"sha256": source["sha256"], "reference": source["reference"]})
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

Это учебный фрагмент; отдельный аппаратный сценарий с ним не заявляется.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.12.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/host/test_target_records.py).
- [config](config.md), [record](record.md).
