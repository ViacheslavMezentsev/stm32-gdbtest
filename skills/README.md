# Навыки для агентов

[English](README.en.md)

Навыки объясняют ИИ-агенту, как применять stm32-gdbtest в проекте прошивки. Каждый навык — каталог
с файлом `SKILL.md`: заголовок YAML (`name`, `description`) и инструкция на русском. Навыки
относятся к той же версии модуля, что и подмодуль, и ссылаются на его документацию.

| Навык | Когда нужен |
| --- | --- |
| [stm32-gdbtest-integrate](stm32-gdbtest-integrate/SKILL.md) | подключить модуль к проекту: подмодуль, каталог `hil/`, описание MCU, `session.toml`, CMake, пресеты, стенд, первый прогон; перевод старого потребителя на опубликованную 0.4.0 |
| [stm32-gdbtest-scenarios](stm32-gdbtest-scenarios/SKILL.md) | написать или переписать сценарий: требование и контракт, место остановки, `check(rows)`, `write(rows)`, `ret`, `refused`, `watch`, `skip`, профиль, стиль, техники TECH-001…019 |
| [stm32-gdbtest-run](stm32-gdbtest-run/SKILL.md) | запустить и разобрать результат: `doctor`, host и hw, CLI, удалённый сервер, пакет, CI, `result.json` и журналы, частые отказы |
| [stm32-gdbtest-results](stm32-gdbtest-results/SKILL.md) | разобрать сохранённые свидетельства без платы: порядок файлов, код сценария, records, JUnit, целостность, экспорт/HTML и обоснованный вывод; в том числе агентом pi на OrangePi |
| [stm32-gdbtest-stand-loop](stm32-gdbtest-stand-loop/SKILL.md) | комплект для автономного стенда, конечные циклы, политика FAIL/SKIP, STOP и передача review.json агенту |
| [stm32-gdbtest-develop](stm32-gdbtest-develop/SKILL.md) | изменить прошивку через DDTT: план, сценарий до исправления, исходный FAIL, исправление, регрессия и разбор свидетельств на плате |

## Подключение навыков в проекте

Навыки лежат в подмодуле: `modules/stm32-gdbtest/skills/`.

- **Claude Code** ищет навыки проекта в `.claude/skills/<имя>/SKILL.md`. Скопируйте нужные каталоги
  туда (на Linux и macOS можно символической ссылкой) и обновляйте копию вместе с gitlink модуля:

  ```powershell
  New-Item -ItemType Directory -Force .claude/skills | Out-Null
  Copy-Item -Recurse -Force modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

  ```sh
  mkdir -p .claude/skills && cp -r modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

- **Другие агенты** (Codex, Gemini, pi и т. п.): укажите в `AGENTS.md` проекта, что перед подключением,
  написанием сценариев, запуском и разбором результатов нужно прочитать соответствующий `SKILL.md` из
  `modules/stm32-gdbtest/skills/`.

Ссылки внутри навыков относительные и ведут в документацию модуля, поэтому работают из подмодуля;
в копии `.claude/skills` пути к документации считаются от `modules/stm32-gdbtest/`.

## Изменение навыков

Навыки — часть модуля: правка сопровождается записью в CHANGELOG и проверкой ссылок
(`python3 ci/run_checks.py docs`). Новое правило сценариев сначала попадает в
[каталог техник](../docs/ru/TESTING_TECHNIQUES.md) и тест стиля, затем — в навык.

На OrangePi навыку результатов достаточно checkout модуля и сохранённых артефактов. Укажи агенту
путь к SKILL.md через инструкцию проекта; отдельная интеграция с конкретной оболочкой pi не требуется.
Проверяй документацию той же версии, что создала результат; для старого формата неизвестные поля
не заполняются предположениями.
