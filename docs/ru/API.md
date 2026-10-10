# API, CLI и миграция

[Документация](index.md) → API · [English](../en/API.md)

[Выпуск v0.3.0](../releases/v0.3.0.md): версия Python 0.3.0; кандидат v0.2.0-rc.1 не публиковался. Исторические сведения ниже сохраняются.

В кандидате v0.4.0 Python-версия 0.4.0, `API_VERSION=2`:
`value`, `fields`, `set_value`, `force_return` удалены. См. [справочник и миграцию](api/index.md).
Выпуск не опубликован; приёмка итогового SHA продолжается.
В schema 2 команды сброса задаются секцией backend в `target.toml`; `api.reset.command`
не влияет на выполнение. Действующую команду читайте через `t.profile.stand["reset_command"]`.
Ключи schema 1 действуют только для OpenOCD; переопределение сброса не меняет host recovery.

Штатные примеры первого пакета и проверка на пяти MCU: [принятые результаты](API_ACCEPTANCE.md).

[Справочник методов и свойств](api/index.md) — отдельные карточки, примеры и версии поддержки.

## Пакет 0.3.0: числа, миграция и алиасы

Исправление кандидата 0.4.0: `evaluate(path, as_type=str)` читает массив `char[]`, размер
которого GDB представляет нулём, по адресу до NUL или `STRING_LIMIT = 256`, как указатель.
Приведение к `const char *` как обход больше не требуется. Для `char[N]` известная граница сохранена;
если у массива неизвестного размера нет адреса, возвращается `ApiError(read_failed)`.
Сигнатура метода не меняется; `API_VERSION=2` задан удалением прежних методов.
ТЗ API 0.3.11, п. 4.18.

Публичные карточки методов — [справочник](api/index.md), разбитый по группам: методы, свойства,
декораторы, классы и ошибки. Контракт закрепляет ревизия ТЗ API 0.3.0-rc.1; модуль реализует все
перечисленные методы и проверен на пяти стендах. Ниже зафиксированы согласованные 04.10.2026 числа и переход
с прежних имён.

| Параметр `api.toml` | Default | Максимум | Где действует |
| --- | ---: | ---: | --- |
| `frames.limit` | 16 | 64 | обход кадров `frames()` |
| `call.depth` | 1 | 2 | глубина вызова в `call()` |
| `call.args_max` | 4 | 8 | число аргументов `call()` |
| `execute.output_limit_chars` | 2048 | 16384 | длина вывода в журнале `execute()` |
| `measurements.series_length` | 5 | 20 | длина серии в сценарии измерений |
| `reset.command` | из backend-а | — | команда сброса `reset()` |
| `app.delay_ms` | из прошивки | — | интервал приложения в проверочной прошивке: от него
  зависят ожидания между проверками |

Значения читаются из `api.toml`; вызов метода может уменьшить `limit`, профиль — увеличить до
максимума. Команду сброса задаёт диалект backend-а: OpenOCD — `monitor reset halt` и
`monitor reset run`, ST-LINK GDB Server и J-Link — `monitor reset`; секция профиля цели для
выбранного сервера (`[openocd]`, `[jlink]`, `[stlink]`) или сессия могут переопределить значение.
Ключ `api.toml` `reset.command` удалён. Лимиты журнала, `breakpoint_limit=4`
и `timeout_s=20` остаются из действующих таблиц.

Переход со прежних имён: в выпуске 0.3.0 эти четыре метода предупреждают `deprecated`,
в кандидате 0.4.0 они удалены.

| Прежнее имя | Новое имя | Примечание |
| --- | --- | --- |
| `value(expression)` | `read(path)` или `evaluate(expression)` | объект читается по пути, выражение вычисляется в GDB; проверить тип результата |
| `fields(expression, expected)` | `check([(name, path, expected), …])` | таблица вычисляет строковые ожидания |
| `set_value(expression, value)` | `write(path, value)` | появляется проверка применённого значения |
| `force_return(expression)` | `ret(value=None)` | возврат становится операцией с результатом |
| `config` / `config_props` | `profile` (разделы, `get`, `origin`) | удалены в 0.3.0 без алиаса; [profile](api/profile.md) |
| `check_range`, `check_near`, `check_in`, `check_table`, `write_memory`, `to_dict` | `check` с `within`/`near`/`one_of`, `check(rows)`, `memory(address, data)`, `snapshot()` | имена кандидата 0.3.0 заменены до выпуска |
| `case(...)` | `test(...)` | без предупреждения: `@case` остаётся основным именем, `@test` — алиас |
| `RecordError` | подкласс `ApiError` | публичный импорт сохраняется |

## Первый пакет: журнал и конфигурация

Выпуск 0.3.0; `API_VERSION=1`, api.toml schema=1. [ТЗ API](../TECHNICAL_SPECIFICATION_API.md). [Принятые результаты](API_ACCEPTANCE.md).

`record(name, data)` добавляет глубокую копию и возвращает None. `records(name=None)` возвращает независимые изменяемые копии: `{'sequence': 1, 'name': 'adc', 'data': ...}`. Имена могут повторяться. Фильтр — точный непустой str; None выбирает всё. Порядок добавления и sequence от 1 сохраняются при фильтрации.

Данные: точные встроенные None/bool/int, конечный float, корректный Unicode str, list и dict со строковыми ключами. Подклассы, tuple, bytes, объекты GDB, циклы и NaN/Inf отвергаются. Повторные ссылки без цикла копируются независимо. Ошибка не расходует бюджет или sequence. Журнал принадлежит одному вызову сценария и сохраняется при clear/reset/continue; автоматического экспорта, чтения MCU и изменения результата проверки нет.

```python
from statistics import mean, stdev
from stm32_gdbtest import RecordError

# После каждого согласованного места остановки:
t.record('adc', {'vdda_mv': t.read('board_measurement.vdda_mv')})
# После серии из минимум двух измерений:
values = [r['data']['vdda_mv'] for r in t.records('adc')]
result = {'mean_mv': mean(values), 'sample_stdev_mv': stdev(values)}
```

Срезы, фильтры и any/all — обычный Python. RecordError(ValueError) импортируется без GDB. code: invalid_name/unsupported_type/invalid_text/non_finite/cycle/limit_exceeded. Для limit_exceeded поле limit: records/nodes/depth/text_bytes/integer_bits. Текст и приоритет одновременных нарушений не фиксированы. Необработанная ошибка — ERROR; check по-прежнему даёт FAIL. MemoryError не подменяется.

| records | Default | Максимум |
|---|---:|---:|
| max_records | 128 | 1024 |
| max_nodes | 4096 | 32768 |
| max_text_bytes | 65536 | 524288 |
| max_depth | 8 | 32 |
| max_integer_bits | 256 | 1024 |

Значения — целые от 1 до максимума, не bool. Записи/узлы/байты ограничивают весь журнал; глубина data считается от 0, integer_bits — int.bit_length. Узлы включают имена, ключи, значения и контейнеры; UTF-8 байты — имена, ключи и строки. Служебная обёртка не учитывается. Это не ограничение RSS или числа удерживаемых копий.

### Явная конфигурация и миграция

```cmake
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${PROJECT_SOURCE_DIR}/hil"
    SESSION_CONFIG "${PROJECT_SOURCE_DIR}/hil/session.toml")
```

```toml
# session.toml: относительные ссылки от его каталога
[config]
target = "target.toml"
api = "api.toml"
image = "full_image.toml" # необязательно
```

```toml
# api.toml
schema = 1
[records]
max_records = 256
[user.measurement]
count = 10
```

`t.profile.get('user.measurement.count')` читает параметр сценария. Разделы `profile`: target/api/user/image с defaults ядра; невыбранный image — None, выбранный — сама политика. `profile.files` содержит sha256 исходных байтов и reference захваченных файлов, `profile.origin(path)` — источник значения (файл, default, переопределение окружением или прогон). Разделы и вложенные контейнеры неизменяемы; массивы становятся tuple. Даты/время и неизвестные поля TOML сохраняются. reference не обещает доступность исходного пути на другом хосте.

SESSION_CONFIG несовместим с PROFILE, --image-policy и STM32_GDBTEST_IMAGE_POLICY. PROFILE_DIR по-прежнему выбирает сценарии. target обязателен; неуказанный api даёт defaults, image — режим секций ELF. Выбранный неверный/отсутствующий файл даёт ERROR до MCU. Неизвестные api-поля доступны сценарию; строгие схемы target/image прежние.

CLI --session принимает прежний генерируемый JSON ELF/GDB/tests с добавленной ссылкой session_config. profile выводится из TOML; после смены target повторите CMake configure/build. Без SESSION_CONFIG нет автопоиска: старые вызовы работают, config_props описывает фактические legacy-источники, api — defaults.

Новый pack сохраняет TOML в служебной капсуле (base64/SHA256/отпечаток defaults); runner/GDB валидируют её без исходных файлов. Для новых пакетов нужен инструмент с поддержкой расширения; старые инструменты не следует использовать. Старые пакеты читаются в legacy-режиме. Для изменения зафиксированной конфигурации подготовьте новый пакет. Это не экспорт record/records.

Статус: опубликован **0.3.0** (Python `0.3.0`, [описание](../releases/v0.3.0.md)),
а в ветке выпуска готовится **0.4.0** (`API_VERSION=2`). Этот номер описывает
поверхность API, а не обещание стабильности релиза 1.0 или версию GDB. Модуль
поставляется Git-подмодулем; установка через pip пока не поддерживается, уникальность
имени перед публикацией ещё предстоит проверить. Требования — [ТЗ](../TECHNICAL_SPECIFICATION.md).

## Подключение из исходного дерева

```cmake
include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    MANIFEST_INPUTS "${CMAKE_CURRENT_SOURCE_DIR}/profile/firmware_FLASH.ld")
```

- `STM32_GDBTEST_SOURCE_DIR` — корень checkout с пакетом `stm32_gdbtest`; в примере
  потребителя это cache PATH.
- Проект обязан включить CTest (`include(CTest)` или `enable_testing()`) и создать
  firmware target до вызова `stm32_gdbtest_attach`.
- Поддерживается один firmware target верхнего каталога CMake, генератор Ninja,
  каталог сборки внутри `PROJECT_SOURCE_DIR`. Сборка, build manifest и подготовка
  и аппаратный запуск работают на Windows и Linux ([Linux-стенд](LINUX_STAND.md)).
- `PROFILE_DIR`, `PROFILE` и пути `MANIFEST_INPUTS` задаются абсолютными. В
  `PROFILE_DIR` находятся `tests/board/test_*.py`, `tests/requirements.md`, при
  использовании контрактов `tests/contracts.json` и `target.toml`. Каталог сценариев
  для новых проектов называется `tests`; прежнее имя `Tests` также поддерживается.
- `PROFILE` — описание MCU отдельным файлом вместо `PROFILE_DIR/target.toml`. Так
  несколько вариантов MCU одной прошивки используют общие сценарии, требования и
  контракты; каждый вариант — своя сборка со своим `PROFILE`:

  ```cmake
  stm32_gdbtest_attach(firmware_target
      PROFILE_DIR "${PROJECT_SOURCE_DIR}/hil"                    # общий tests/
      PROFILE "${PROJECT_SOURCE_DIR}/hil/profiles/${MCU}.toml")  # G474.toml, G431.toml
  ```
- `MANIFEST_INPUTS` добавляет файлы в снимок manifest и в зависимости перелинковки.
- `SELF_TESTS` включает host-тесты самого модуля (`host.hwtest`); потребителю не нужен.
- stm32-cmake-yml не является зависимостью API.

CMake создаёт тесты: `hw.<ID>` (аппаратный, метки `hw` и метки сценария,
`RESOURCE_LOCK stm32_swd`), `prepare.<ID>` (подготовка без оборудования, метки
`host` и `prepare`) и `host.traceability`. Цель `check-hw` запускает весь CTest
с отчётом JUnit.

Cache `STM32_GDBTEST_GDB` выбирает GDB с Python, `STM32_GDBTEST_STAND` — локальный
TOML стенда. Остальные переменные CMake с этим префиксом внутренние. Генерируемые
`session.json`, `tests.cmake` и `build-manifest.json` не редактируются вручную.
Функция `stm32_gdbtest_register` — внутренняя.

## Сценарии Python

```python
from stm32_gdbtest import case

@case("HW_GPIO", timeout_s=20, labels=("gpio",), contracts=("gpio_macros",))
def gpio(t):
    t.reach("loop")
    t.check("GPIOC clock", t.evaluate("__HAL_RCC_GPIOC_IS_CLK_ENABLED()"), 1)
```

Пример требует прошивки с функцией `loop` и объявленного контракта `gpio_macros`;
это не универсальный тест любого STM32.

- Декоратор импортируется обычным Python без модуля `gdb`. При сборе код теста не
  выполняется: ID, timeout, labels и contracts читаются из AST и должны быть литералами.
- ID — `HW_[A-Z0-9_]+`; `timeout_s` — целое 1…300 с (по умолчанию 20); labels —
  `[a-z0-9_-]+`; имена контрактов — `[a-z][a-z0-9_]+`.
- Декоратор называется `case` без псевдонима. Тест — функция верхнего уровня с одним
  параметром Target; агент вызывает её после reset и остановки в `main`.
- Вспомогательный код проекта доступен из корня потребителя. Тестовые hooks в
  прошивку не добавляются.

Публичные операции переданного Target (модуль `target` импортируется только в GDB):

| Операция | Контракт |
| --- | --- |
| [`check(name, actual, expected)`](api/check.md) | Запись результата; несовпадение вызывает `CheckFailed` → FAIL |
| [`read(path)`](api/read.md) / [`evaluate(expression)`](api/evaluate.md) | Типизированное чтение объекта / вычисление выражения GDB/C |
| [`reach(location, condition=None)`](api/reach.md) | Временная аппаратная точка, `continue`, проверка причины остановки, кадра и условия (`when=` — прежнее имя `condition`); имя кадра сравнивается без `[clone …]` и параметров (клоны LTO) |
| [`breakpoint(location, temporary=False, *, condition=None)`](api/breakpoint.md) | Аппаратная точка (`Point`) с проверкой pending и бюджета профиля; `when=` — прежнее имя `condition` |
| [`write(path, value)`](api/write.md) | Явная запись с проверкой и журналом before/after; допустимость записи в MMIO проверяет автор |
| [`ret(value=None)`](api/ret.md) | Принудительный return из текущего кадра с результатом и журналом; тело функции не выполняется |
| [`clear()`](api/clear.md) | Удалить точки останова Target, включая точки на fault handlers |

`boot`, `close`, `on_stop`, `report`, `owned`, `stops` и создание Target —
внутренний жизненный цикл агента. Вызовы GDB допустимы только в его основном
потоке. `-g3` сохраняет макросы, но не неиспользуемые функции и символы;
см. [HAL-макросы](HAL_MACRO_GUIDE.md) и [контракты](CONTRACTS.md).

## CLI

Из корня checkout модуля (из другой папки — по абсолютному пути `stm32_gdbtest/cli.py`):

```powershell
python -B -m stm32_gdbtest --version
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/tests/board --requirements examples/minimal-consumer/profile/tests/requirements.md
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --prepare-only
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --stand path/to/stand.local.toml
python -B -m stm32_gdbtest doctor --stand path/to/stand.local.toml
```

Логическое имя CLI — `stm32-gdbtest`; отдельный исполняемый файл появится при упаковке.

| Параметр `run` | Назначение |
| --- | --- |
| `--session` или `--package`, `--test` | Сгенерированный `session.json` или пакет подготовленного запуска и ID сценария |
| `--gdb`, `--workdir` | Для `--package`: GDB стенда (иначе поиск как у `doctor`) и каталог распаковки (по умолчанию `build/ddtt-packages`) |
| `--stand` | Локальный стенд; порядок выбора: `--stand` → `STM32_GDBTEST_STAND` → `session.stand`; с таблицей `[remote]` сервер запускается на хосте стенда по SSH, в отчёте — `server_host`, журнал SSH — `tunnel.log` |
| `--timeout` | Внешний предел времени GDB, 0 < t ≤ 300 с; по умолчанию `timeout_s` сценария |
| `--identity-policy warn\|strict` | Политика DEV_ID; порядок: CLI → `STM32_GDBTEST_IDENTITY_POLICY` → `warn` |
| `--image-policy` | Политика полного образа; альтернатива — абсолютный `STM32_GDBTEST_IMAGE_POLICY` |
| `--prepare-only` | Только шаги до GDB-сервера, без оборудования |

`--prepare-only` выполняет все шаги до GDB-сервера: стенд (если выбран), профиль,
снимок ELF, build manifest, запрошенные контракты, секции и образ, включая полный
режим. Блокировка отладчика, сервер и подключение не используются; отчёт получает
`mode: prepare` и `hardware_accessed: false`. Стенд в этом режиме необязателен,
а если выбран — проверяется целиком, включая mapping J-Link.

`doctor [--gdb PATH] [--stand TOML] [--json]` проверяет окружение без обращения к
отладчику: host Python, GDB-Python ≥ 3.11 и binutils рядом с ним, CMake и Ninja,
каталог блокировок, стенд (для OpenOCD — наличие `interface/stlink.cfg`) и на Linux —
ST-Link и J-Link на USB с правами доступа. Итог — строки OK/WARN/FAIL (`--json` — список
`{name, status, detail}`); код 1 при FAIL. GDB ищется так: `--gdb` → `STM32_GDBTEST_GDB` →
`arm-none-eabi-gdb-py3`/`arm-none-eabi-gdb` в `PATH` → `bin` в `ARM_TOOLCHAIN_ROOT` → на
Windows каталог xPack по умолчанию в профиле пользователя. Для стенда с `[remote]`
локальные проверки OpenOCD и USB заменяются проверками хоста стенда по SSH (`remote`,
`remote-server`, `remote-lock`, `remote-usb`, предел 40 с).

`pack --session S --output P.zip [--test ID …] [--include PATH …]` готовит сценарии без
оборудования и пишет пакет подготовленного запуска; `run --package` проверяет SHA-256
каждого файла пакета и добавляет в отчёт поле `package`
([аппаратный CI](HARDWARE_CI.md)).

`collect --cmake/--workspace` — интерфейс генерации CMake, вручную обычно не нужен.

Коды `run`: PASS — 0, FAIL — 1, ERROR — 2; ошибка аргументов также даёт 2. Отказ
до создания каталога запуска не гарантирует JSON/JUnit. Ожидаемый отказ сохраняет
ERROR и не превращается в PASS.

Стабильные схемы: target 1, реестр контрактов 1, build manifest 1, runtime
compatibility 1, политика образа 1, пакет подготовленного запуска 1. `session.json` — внутренний артефакт без
обещания стабильной схемы. Прямые вызовы `runner`, `contracts`, `processes` —
внутренний API разработки; потребители используют CMake, CLI и операции Target.
Подробности: [подключение](GETTING_STARTED.md), [manifest](MANIFESTS.md),
[identity](TARGET_IDENTITY.md), [GDB-серверы](BACKENDS.md),
[владение отладчиком](DEBUGGER_OWNERSHIP.md). `STM32_GDBTEST_LOCK_DIR` задаёт на Linux
базовый каталог блокировок: по умолчанию системный каталог временных файлов (`/tmp`
или `TMPDIR`), внутри — `stm32-gdbtest-locks`.

## Проверка образа

По умолчанию Flash сравнивается по загружаемым секциям ELF (LMA), промежутки не
проверяются. BIN формируется только из этих секций с заполнением промежутков 0xFF.
Нужны GNU `arm-none-eabi-objdump` и `arm-none-eabi-objcopy` рядом с GDB. Это не
проверка CRC всей области.

Полный образ: `run --image-policy file.toml` или `STM32_GDBTEST_IMAGE_POLICY`
(CLI приоритетнее) выбирает диапазон `[image]` schema 1. Канонический BIN,
транспортный ELF, CRC-32/ISO-HDLC по readback, поля отчёта и ограничения —
[образы и CRC](IMAGES.md). Режим не добавляет код или CRC-поле в прошивку; CRC
считается на ПК, а не периферией MCU.

## Переход с hwtest

| Было | Стало |
| --- | --- |
| `from hwtest import case` | `from stm32_gdbtest import case` |
| `hwtest/cli.py` | `stm32_gdbtest/cli.py` или `python -m stm32_gdbtest` |
| `hwtest/cmake/HwTest.cmake` | `stm32_gdbtest/cmake/STM32GDBTest.cmake` |
| `hwtest_attach` | `stm32_gdbtest_attach` |
| `HWTEST_SOURCE_DIR` / `HWTEST_GDB` / `HWTEST_STAND` | `STM32_GDBTEST_SOURCE_DIR` / `STM32_GDBTEST_GDB` / `STM32_GDBTEST_STAND` |
| `HWTEST_IDENTITY_POLICY` | `STM32_GDBTEST_IDENTITY_POLICY` |

Старые псевдонимы импорта, CLI и CMake не предоставляются. Переменные окружения
`HWTEST_STAND` и `HWTEST_IDENTITY_POLICY` дают явный отказ runner, чтобы устаревшее
указание стенда не было молча проигнорировано. Внутренние переменные `RUN` и
`CONTRACT_REQUEST` тоже переведены на новый префикс; их формирует host.

Порядок миграции: обновить импорты, локальные presets и команды, перенести свои
значения cache на новые имена, убрать старые переменные окружения и заново выполнить
configure и build. Старый CTest без configure содержит пути прежнего пакета.
Сохранены имена build/test presets, `check-hw`, `host.hwtest`, каталоги отчётов
`hwtest`, ID `HW_*`, форматы TOML/JSON и пространство имён блокировки. Миграция не
требует тестовых hooks в прошивке и не означает поддержки произвольного STM32,
ОС кроме Windows и Linux для аппаратного запуска или автоматической остановки
процессов после аварии host.

CMSIS fixture F030: API ядра не изменён. `app_delay` в этом примере теперь задаёт миллисекунды SysTick (500), `app_state.ticks` остаётся счётчиком циклов. Четыре сценария описаны в [протоколе](F030_CMSIS_BASELINE.md).

API ядра не изменён. Счётчик board_timer_events — состояние F030 fixture, не публичный API. [TIM3/IRQ](F030_CMSIS_TIMER.md).

ADC/DMA F030: сырые отсчёты и timeout, API ядра без изменений. [ADC/DMA](F030_CMSIS_ADC_DMA.md).

F030: преобразование ADC и численные сценарии, API ядра без изменений. [ADC units](F030_CMSIS_ADC_UNITS.md).

F030 Sleep/WFI: профильные сценарии через GDB unwind, API ядра не меняется. [Sleep evidence](F030_CMSIS_SLEEP.md).

F030 RTC: Alarm A на LSI, 16/16 HW PASS, HAL восстановлен. API ядра без изменений. [RTC](F030_CMSIS_RTC.md).

F030: проверка занятого ADC, API без изменений. [Протокол](F030_ADC_BUSY.md).

F030: RTC deadline через инъекцию аргумента, API без изменений. [Протокол](F030_RTC_DEADLINE.md).

Собственные профили/примеры и новые пакеты используют `tests`; чтение старых `Tests` сохранено. Локальные remote-стенды — `<profile>-<backend>.remote.toml` (`openocd`, `jlink`, `stlink`), исключённые из Git. После переименования повторить configure. [Соглашения](maintenance.md).

[Автономная HAL-регрессия F030](F030_HAL_REGRESSION.md): тестовый consumer, без изменения API.

[CI: уровень hal](testing.md) добавляет проверку fixture, публичный API/схемы не меняются.

## Сохранение результатов пакетов (rc.2)

При повторном run --package исходники распаковываются в новый
`<workdir>/<16 знаков SHA-256>/sessions/session-*`. Отчёты каждого запуска остаются
в его `<workdir>/<16 знаков SHA-256>/sessions/session-*/runs`. Пути сессии следует брать из
метаданных, не конструировать как `<хэш>/firmware.elf`. Старые пакеты schema 1
читаются без изменений; API_VERSION=1. Каталог источников сохраняется для
разбора ошибок; автоматической очистки нет. Удалять старые build можно только
после сохранения нужных доказательств и завершения использующих их запусков.

До исправления новое открытие пакета удаляло весь каталог хэша, включая runs.
Утерянные JSON не восстанавливаются из summary: нужен повтор проверки.

F401 baseline добавляет только fixture и offline CI; API_VERSION=1 и схемы без изменений. [F401](F401_CMSIS_BASELINE.md).

F401 ADC/DMA изменяет только fixture. Общая функция измерений F4 теперь adc_convert_f4_factory; это символ тестовой firmware, не публичный API модуля. API_VERSION=1, схемы неизменны. [F401 ADC/DMA](F401_CMSIS_ADC_DMA.md).

F401 RTC/Sleep расширяет только fixture. rtc_f4.c и векторы общие с F411; публичный API и схемы не изменены. F411 после переноса проверен offline. [F401 RTC/Sleep](F401_CMSIS_RTC_SLEEP.md).

Добавлен профиль fixture f429zi с семью сценариями. Публичный API, схемы и версия неизменны. [F429 baseline](F429_CMSIS_BASELINE.md).

F429 fixture дополнена ADC/DMA и арифметикой; общий converter, публичный API, схемы и версия неизменны. [F429 ADC/DMA](F429_CMSIS_ADC_DMA.md).

F429 подключён к общей RTC-реализации F4 и таблице векторов; алгоритм RTC, публичный API и схемы не меняются. [F429 RTC/Sleep](F429_CMSIS_RTC_SLEEP.md).

[HAL F030: пять GPIO/RCC-техник и варианты исходников](F030_HAL_GPIO_RCC.md).

## Захват журнала результатов (Unreleased)

В session.toml можно включить обязательный захват:

```toml
[results]
capture = true
```

По умолчанию false; сценарии не требуют миграции. Capsule/pack переносит настройку;
prepare-only не требует журнала. После возврата или исключения сценария, до close,
runner сохраняет весь records() в records.json рядом с result.json. Методы Target не меняются.
Схема 1: schema, run_id, case_id, records (sequence/name/data). run_id — непрозрачное имя
каталога запуска (UTC, ID, PID). Лимит 16 MiB; публикация через полностью записанный временный
файл в том же каталоге. Существующий файл отвергается. Каталог принадлежит одному запуску;
конкурентная запись сторонними процессами не поддерживается. Гарантии при отключении питания нет.

result.capture.status: saved/unavailable/error; completion: normal (возврат), interrupted
(исключение сценария), unknown (сценарий не начат или отчёт не получен). Saved содержит path,
sha256, count; error — причину {type, message}. Host проверяет хеш, принадлежность и схему.
result.status сохраняет исходный вердикт. command_code: PASS/FAIL/ERROR → 0/1/2;
при отказе обязательного захвата → 2, с отдельным artifact_error. Код GDB соответствует status.
При принудительном завершении журнал может отсутствовать; пустой файл вместо него не создаётся.

При отказе захвата JUnit добавляет инфраструктурный testcase <ID>.capture с error, сохраняя
исходный testcase. Счётчик tests включает этот testcase, а не дополнительную проверку MCU.
Консоль раздельно показывает Scenario, Capture и Command. CSV/HTML в этот этап не входят.

## Обработка сохранённых результатов (Unreleased)

Команды `results export` и `results verify`: [контракт, CLI и примеры](RESULTS.md).
Журнал хранит произвольные данные; проекции измерений задаются отдельно. Методы Target и существующие сценарии менять не нужно.

`results report` формирует автономный JSON/HTML по индексу и необязательному экспорту; [сводка и темы](RESULTS.md#сводка-jsonhtml-unreleased).

В HTML-сводке доступны переключатели темы и обычного/экспертного представления; данные не меняются.

Составные приёмы на существующем API: [события и интервалы](TESTING_TECHNIQUES.md#tech-011), [ожидание изменений](TESTING_TECHNIQUES.md#tech-015), [C++-контекст](TESTING_TECHNIQUES.md#tech-019).

### reach и кавычки C++ (Unreleased)

Для перегрузки используйте полную сигнатуру. Исправлен ложный FAIL имени кадра с одной внешней парой одинарных кавычек GDB; строки без кавычек работают как раньше. Миграция не требуется; для версии 0.3.0 обход — убрать внешние кавычки. [Контракт](api/reach.md).


## SKIP (Unreleased)

[skip(reason)](api/skip.md) — завершение неприменимого сценария; причина, records, код77 и миграция.

## st-util и schema 2 (v0.4.0)

В стенде выберите `backend = "st-util"`; в target.toml schema 2 можно добавить
`[st-util]` с `reset_halt = "monitor reset"` либо оставить встроенное значение.
Существующие секции и сценарии менять не требуется. `profile.stand["backend"]`
теперь может быть `st-util`; обновите собственные списки допустимых серверов.
Методы Target и API_VERSION=2 не меняются. [Конфигурация и ограничения](BACKENDS.md#st-util-v040).

## Завершение удалённого сервера (v0.4.0)

В result.json `status_before_cleanup` сохраняет исход до recovery/cleanup. Блок `remote_server`
содержит фактический POSIX `returncode`, `reason`, `signals`, `ssh_returncode` и при отказе `error`.
Например, SIGABRT — returncode -6, хотя SSH возвращает250. Неизвестный код — null, не0.
Авария cleanup даёт итоговый ERROR и cleanup_error, сохраняя checks, исходный error и skip_reason.
Потребители должны использовать итоговый status; status_before_cleanup нужен для диагностики.
Target API и API_VERSION не меняются. Для st-util ожидается exit0 после запрошенного завершения;
SIGKILL, heartbeat timeout или отсутствие подтверждения — ERROR. Это не гарантия безопасности USB.

Для st-util добавлены `recovery_wait` (если требовался recovery), `shutdown_wait` и
`remote_server.idle`: `ready`, `reason`, `elapsed_s`, `limit_s`. Последнее поле подтверждает
наблюдение idle на хосте стенда; без него exit0 недостаточно. Ожидание Listening ограничено5с,
host recovery —10с; итоговое ожидание SSH —25с с учётом cleanup. Эти поля диагностические:
для принятия результата используйте итоговый status. [Жизненный цикл](LINUX_STAND.md#диагностика-завершения).
