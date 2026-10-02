# Исследование 2: адаптивное дерево сценариев

[Документация](../../../ru/index.md) · [English](../en/index.md)

Имитационная Python-модель динамической активации веток. GDB, MCU, отладчики и
производственный runner не используются. Публичный API и ТЗ проекта не изменены.

- [План и семантика](plan.md) — структура папок, вход/выход, выбор следующего теста.
- [Отчёт S1](s1.md) — ожидаемые переходы, проверки, ограничения и воспроизведение.
- [HTML-проигрыватель](../results/player.html) — слайдер и Play/Pause по записанным состояниям.
- [Снимки всего дерева](../results/snapshots.json), [проверка эталона](../results/verification.json).
- [Движок](../../../../tools/research/adaptive_tree/engine.py),
  [дерево примера](../../../../tools/research/adaptive_tree/fixtures/bringup/tree/node.json),
  [независимый эталон](../../../../tools/research/adaptive_tree/fixtures/bringup/expected.json).

Ветка `codex/adaptive-test-tree` от локального main `da42cd7`. Два fetch завершились
сбросом соединения; актуальность GitHub при создании не подтверждена. Первое
исследование GDB Python осталось в `codex/rc3-api-r1` на `fffa11d` и сюда не слито.

[Сводка проверок](../results/checks.json): модель14/14, Windows/Linux host, docs CI и браузер.
