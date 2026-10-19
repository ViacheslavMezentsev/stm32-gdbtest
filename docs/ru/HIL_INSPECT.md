# Проверка связей HIL без запуска

[Документация](index.md) · [English](../en/HIL_INSPECT.md)

`inspect` проверяет выбранные настройки и показывает связи HIL, backend и SVD.
Команда не запускает CMake, GDB, серверы, эмуляторы или сценарии, не подключается
к плате и сети. Метаданные сценариев собираются через AST без импорта Python.
Успех означает структурную корректность, а не PASS сценариев или квалификацию платы.

```powershell
# Фактические настройки уже сконфигурированной сборки
python -m stm32_gdbtest inspect --session build/debug/hwtest/session.json

# Исходная компактная структура, до сборки
python -m stm32_gdbtest inspect --config hil/F103CB/session.toml --profile-dir hil/common --project-root .

# Разнесённая структура, дополнительный набор и машинный отчёт
python -m stm32_gdbtest inspect --config hil/sessions/f411.toml --profile-dir hil --test-dir hil/extra/tests --format json --output hil-inspect.json
```

`--session` и `--config` исключают друг друга. В режиме session корни сценариев
берутся из JSON; `--profile-dir`/`--test-dir` запрещены. В режиме config требуется
`--profile-dir`: используется его tests/ (или legacy Tests/), затем board/test_*.py.
Повторяемый `--test-dir` задаёт дополнительный корень с board/ и requirements.md.
Поиск не рекурсивный; одинаковые canonical корни и повторные ID — ошибки.
Обе структуры каталогов равноправны, нового TOML-реестра не требуется.

`--stand` выбирается как у runner: CLI → STM32_GDBTEST_STAND → session.stand.
Без стенда выдаётся WARN stand.not_selected. Наличие executable не доказывает
его работоспособность. OpenOCD scripts и удалённые инструменты помечаются DEFERRED:
их разрешает сервер. Для Renode проверяется самостоятельный REPL; QEMU — штатная
схема machine. Никаких запусков `--version`, SSH или автоматического выбора стенда.

## Пути и снимки

CLI-пути разрешаются от cwd. TOML config/data и mmio.svd — от содержащего session.toml.
Относительные поля runtime JSON сохраняют зависимость от cwd; каталог JSON не становится
их базой. `--project-root` влияет только на представление отчёта. Executable использует
штатный PATH/expand_path; Renode platform — каталог stand. Не все поля TOML поддерживают
подстановки переменных. Ссылки вне проекта допустимы; junction/symlink показываются
исходным и canonical путями. Старые правила runner не меняются.

При `_config_capsule` проверяются захваченные байты и хеши, без повторного чтения исходных
TOML/SVD. Наборы сценариев и ELF остаются файловыми ссылками. Legacy runtime без session
и ZIP напрямую не поддерживаются. Можно проверить распакованную runtime-сессию.
SVD проверяется штатным ограниченным парсером, включая права/эффекты и запрещённые XML
конструкции. FOUND не означает VALID. Отсутствие SVD разрешено для конфигурации без MMIO.
Семантика SVD не доказывает соответствие реальному MCU. contracts.json проверяется как
JSON, без ELF-preflight; ELF проверяется только на наличие.

## Вывод и JSON schema 1

`--format text|json` (по умолчанию text); без `--output` — stdout. Родительский каталог
отчёта должен существовать. Внешние абсолютные пути заменяются `<external>`;
`--local-details` показывает локальные пути. Содержимое ключей, serial/hostname стенда,
сырой TOML и текст исключений не выводятся. Имена файлов внутри проекта остаются видимыми.

| Поле | Содержание |
|---|---|
| schema, scope, runtime_checked | 1, structure, false |
| selection | mode=config/session, source=disk/capsule, stand=none/cli/env/session |
| nodes | id, role, path, resolved_path, origin, status, sha256 |
| edges | source, target, field, base_kind, resolver, status |
| scenarios | id, function, path, labels, contracts, timeout_s |
| svd | source, availability, semantics, registers |
| diagnostics | code, severity, node, field, message |
| summary | ERROR/WARN/DEFERRED counts |
| configuration_valid | true только при отсутствии ERROR |
| backend | присутствует после успешного разбора стенда |

Статусы узлов/связей: FOUND/MISSING/DEFERRED. origin обозначает disk/capsule/ast либо
внешний resolver. Пути и sha256 могут быть null; executable, SSH и ELF не хешируются.
Для конфигурации хеш относится к проверенному снимку. В capsule пути null.
SVD availability: NOT_CONFIGURED/FOUND/MISSING; semantics: NOT_CHECKED/VALID/INVALID;
registers — число регистров или null. При ошибке снимка сведения могут быть неполными.
После ERROR граф может быть частичным; дальнейшие проверки не гарантированы.

Коды диагностики стабильны; message — текстовая форма кода, не основание для парсинга:

- input.conflict/profile_required; file.missing;
- runtime.invalid/legacy_unsupported/cwd_dependent (последний WARN);
- config.source/session/reference/target/image/data/api_schema/api_parameter/conflict/stale_selection/transport/invalid;
- configuration.invalid; svd.source/integrity/invalid;
- scenarios.directory_missing/duplicate_root/invalid; requirements.invalid;
- backend.invalid/environment_mismatch; stand.not_selected (WARN).

Код процесса 0: нет ERROR. Код 2: ERROR либо WARN при `--warnings-as-errors`.
DEFERRED не превращается в ошибку этой опцией. Ошибка записи — stderr
`ERROR: output.unwritable`, код 2; ошибки аргументов также код 2.

В 0.5.0 команда добавлена без изменения Target API. Она дополняет `doctor` и
`run --prepare-only`: последние выполняют другие проверки и могут запускать инструменты.
