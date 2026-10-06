# Навыки для агентов

[English](README.en.md)

Навыки объясняют ИИ-агенту, как применять stm32-gdbtest в проекте прошивки. Каждый навык — каталог
с файлом `SKILL.md`: заголовок YAML (`name`, `description`) и инструкция на русском. Навыки
относятся к той же версии модуля, что и подмодуль, и ссылаются на его документацию.

| Навык | Когда нужен |
| --- | --- |
| [stm32-gdbtest-integrate](stm32-gdbtest-integrate/SKILL.md) | подключить модуль к проекту: подмодуль, каталог `hil/`, описание MCU, `session.toml`, CMake, пресеты, стенд, первый прогон; перевод старого потребителя на 0.3.0 |
| [stm32-gdbtest-scenarios](stm32-gdbtest-scenarios/SKILL.md) | написать или переписать сценарий: требование и контракт, место остановки, `check(rows)`, `write(rows)`, `ret`, `refused`, `watch`, профиль, стиль, техники TECH-001…018 |
| [stm32-gdbtest-run](stm32-gdbtest-run/SKILL.md) | запустить и разобрать результат: `doctor`, host и hw, CLI, удалённый сервер, пакет, CI, `result.json` и журналы, частые отказы |

## Подключение навыков в проекте

Навыки лежат в подмодуле: `modules/stm32-gdbtest/skills/`.

- **Claude Code** ищет навыки проекта в `.claude/skills/<имя>/SKILL.md`. Скопируйте три каталога
  туда (на Linux и macOS можно символической ссылкой) и обновляйте копию вместе с gitlink модуля:

  ```powershell
  New-Item -ItemType Directory -Force .claude/skills | Out-Null
  Copy-Item -Recurse -Force modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

  ```sh
  mkdir -p .claude/skills && cp -r modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

- **Другие агенты** (Codex, Gemini и т. п.): укажите в `AGENTS.md` проекта, что перед подключением,
  написанием сценариев и запуском нужно прочитать соответствующий `SKILL.md` из
  `modules/stm32-gdbtest/skills/`.

Ссылки внутри навыков относительные и ведут в документацию модуля, поэтому работают из подмодуля;
в копии `.claude/skills` пути к документации считаются от `modules/stm32-gdbtest/`.

## Изменение навыков

Навыки — часть модуля: правка сопровождается записью в CHANGELOG и проверкой ссылок
(`python3 ci/run_checks.py docs`). Новое правило сценариев сначала попадает в
[каталог техник](../docs/ru/TESTING_TECHNIQUES.md) и тест стиля, затем — в навык.
