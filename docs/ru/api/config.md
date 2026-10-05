# config

[API](index.md) · [English](../../en/api/config.md)

`config: Mapping`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.2.0.dev0 → 0.2.0rc1 |
| Контракт принят в ТЗ API | 0.2.0; §4.11 |
| API_VERSION | 1 |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |
| Синоним прежнего имени | config -> settings (алиас действует без предупреждений до 1.0, удаление в 0.4.0) |

Новый пакет реализован; `0.2.0rc1` — локальный кандидат, не опубликованный стабильный релиз.

## Назначение

Глубоко неизменяемое отображение api/target/image зафиксированного запуска с применёнными defaults. Свойство, не метод.

## Контракт и ограничения

Неуказанный api даёт defaults, image — None. Неизвестные api-поля сохранены; списки становятся tuple, TOML-типы сохраняются. Доступ к неизвестному ключу даёт KeyError; изменение запрещено. Источники задаются SESSION_CONFIG, не перечитываются на каждом обращении.

Для примера ниже выберите api.toml из session.toml и задайте параметры:

```toml
# session.toml
[config]
target = "target.toml"
api = "api.toml"
```

```toml
# api.toml
schema = 1
[user.measurement]
count = 10
```

## Пример

```python
settings = target.config["api"]["user"]["measurement"]
count = settings["count"]
target.check("valid series count", type(count) is int and 2 <= count <= 20, True)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.11.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [config_props](config-props.md), [record](record.md).
