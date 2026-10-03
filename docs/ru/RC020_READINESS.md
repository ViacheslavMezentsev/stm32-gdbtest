# Кандидат v0.2.0-rc.1: состав и приёмка

[Документация](index.md) · [English](../en/RC020_READINESS.md)

Согласован 03.10.2026. Python `0.2.0rc1`, ТЗ API **0.2.2**, API_VERSION=1,
api.toml schema=1, общее ТЗ **0.64**. Кандидат готовится локально; тег и публикация не выполнены.

## Состав

- record/records, публичный RecordError и неизменяемые config/config_props.
- Явный SESSION_CONFIG, session.toml и захваченный снимок TOML в GDB/пакете.
- Совместимость прежних session.json, PROFILE_DIR и пакетов.
- Пять CMSIS-профилей, HAL F030, техники таблиц и статистики измерений.
- Стек/контекст, experimental read/finish, RTOS и адаптивный движок не включены в API.

## Миграция с v0.1.0-rc.2

1. Обновить закреплённый gitlink модуля до проверенного SHA кандидата и повторить CMake configure.
   Установка через pip не предусмотрена.
2. Старые PROFILE_DIR, target.toml, session.json и сценарии продолжают работать.
   Для использования config из новых TOML выбрать SESSION_CONFIG явно.
3. Создать session.toml с `[config]`, `target = "target.toml"`, `api = "api.toml"`;
   при full-image добавить `image = "full-image.toml"`. Пути разрешаются относительно session.toml.
4. В api.toml задать `schema = 1`, `[records]` и при необходимости пользовательские секции.
   Неизвестные поля доступны сценарию; известные ограничения проходят валидацию.
5. Не совмещать SESSION_CONFIG с прежним выбором PROFILE или image override.
   session.json остаётся генерируемым дескриптором запуска; вручную заменять его TOML не нужно.
6. record/records — журнал одного вызова сценария, без автоматического экспорта.
   Новый пакет со снимком конфигурации запускать новой версией модуля.

Примеры и ограничения — [API](API.md), [техники](TESTING_TECHNIQUES.md),
[интеграция](../research/api-extension/ru/core-integration.md).

## Проверка кандидата

Выполняется. Не считать предыдущие аппаратные результаты проверкой текущего SHA.
План: полный Docker docs/format/host и матрица GCC13/14/15 × пять CMSIS;
HAL GCC13; настоящий Git-подмодуль потребителя; Windows lifecycle F030/OpenOCD,
F103/J-Link, F411/OpenOCD и F411/ST server с восстановлением.

Предыдущая полная кампания: [103 CMSIS + 22 HAL + 1 пример](../research/api-extension/ru/scenario-migration.md).
Предупреждение Flash F103 сохранено. Orange Pi/SSH на этом этапе не перепроверяется.
Слияние, подписанный тег и публикация — отдельные действия владельца после приёмки.
