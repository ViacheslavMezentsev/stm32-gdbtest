# Изменения между выпусками

[Документация](index.md) · [English](../en/RELEASE_CHANGES.md)

Краткая памятка для пользователя; полная история — [CHANGELOG](../../CHANGELOG.md).
Рабочие руководства описывают 0.5.x. Номер DDTT и ревизия ТЗ независимы от версии пакета.

| Переход | Что изменилось для пользователя | Что сделать |
| --- | --- | --- |
| Ранние кандидаты → 0.3.0 | Навигация, watch, call/ret, таблицы, profile и records; переименование прежних операций | Использовать карточки API вместо старых имён; журнал сценария не является автоматическим файлом |
| 0.3.x → 0.4.0 | API 2, удаление старых имён, захват/экспорт records, SKIP, st-util и расширение схем | Явно настроить capture; различать сценарий, захват и код команды |
| 0.4.0 → 0.4.1 | Документация, навыки и DDTT; без изменения API 2 | Уточнить маршрут разработки и ограничения свидетельств |
| 0.4.x → 0.5.0 | API 3, async-навигация, wait/halt, ограниченный call, полный memory, однократный RHS, C++ preflight, MMIO/SVD, Renode/QEMU, inspect и квалификация DDTT | Следовать [миграции](MIGRATION_050.md); hidden calls вынести в call, периферию — в MMIO; повторить приёмку потребителя |
| 0.5.0 → 0.5.1 (в подготовке) | Актуализация документов, TECH-021–026 и нейтральный пример состояний/очереди | API 3 сохраняется; использовать [пример](../../tests/stateful-buffer/README.md), различать ожидаемый FAIL и ошибку инфраструктуры |

Планы memory/write и C++ preflight первоначально назывались «0.4.2»; они вошли в 0.5.0,
а не в отдельный выпущенный 0.4.2. В старом write строковый RHS мог вычисляться повторно;
в API 3 RHS однократен, LHS должен быть стабильным, скрытые вызовы запрещены.
Обходы старого evaluate для char[] без размера и reach с внешними кавычками больше не нужны:
пользуйтесь действующими карточками [evaluate](api/evaluate.md) и [reach](api/reach.md).

## Исторические материалы

Срезы сохранены для воспроизводимости; их прежние «текущие» статусы не относятся к 0.5.x.

- [API.md](../archive/pre-050/ru/API.md)
- [STATUS.md](../archive/pre-050/ru/STATUS.md)
- [API_ACCEPTANCE.md](../archive/pre-050/ru/API_ACCEPTANCE.md)
- [HARDWARE_METRICS.md](../archive/pre-050/ru/HARDWARE_METRICS.md)
- [RUN_LAYOUTS.md](../archive/pre-050/ru/RUN_LAYOUTS.md)
- [VERSIONING.md](../archive/pre-050/ru/VERSIONING.md)
- [API030_PLAN.md](../archive/pre-050/ru/API030_PLAN.md)
- [API040_SCENARIOS.md](../archive/pre-050/ru/API040_SCENARIOS.md)
- [RC020_READINESS.md](../archive/pre-050/ru/RC020_READINESS.md)
- [RC2_READINESS.md](../archive/pre-050/ru/RC2_READINESS.md)
- [RELEASE040_SCOPE.md](../archive/pre-050/ru/RELEASE040_SCOPE.md)
