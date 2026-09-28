# API, CLI и миграция

[Документация](index.md) → API · [English](../en/API.md)

Статус: версия разработки **0.1.0.dev0**, `API_VERSION = 1`. Это номер описанной
поверхности API, а не обещание стабильности релиза 1.0 и не версия GDB. Модуль
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
- `PROFILE_DIR` и пути `MANIFEST_INPUTS` задаются абсолютными. В `PROFILE_DIR`
  находятся `target.toml`, `Tests/board/test_*.py`, `Tests/requirements.md` и при
  использовании контрактов `Tests/contracts.json`.
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
    t.check("GPIOC clock", t.value("__HAL_RCC_GPIOC_IS_CLK_ENABLED()"), 1)
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
| `check(name, actual, expected)` | Запись результата; несовпадение вызывает `CheckFailed` → FAIL |
| `value(expression)` | `gdb.parse_and_eval`, отказ для optimized-out, возвращает `int` |
| `fields(expression, expected)` | Поэлементное сравнение скалярных полей с `int` или C-выражением |
| `reach(function, when=None)` | Временная аппаратная точка, `continue`, проверка причины остановки, кадра и условия |
| `breakpoint(function, temporary=False, when=None)` | Аппаратная точка с проверкой pending и бюджета профиля |
| `set_value(expression, value)` | Явная запись с журналом before/after; допустимость записи в MMIO проверяет автор |
| `force_return(expression)` | Принудительный return из текущего кадра с журналом; тело функции не выполняется |
| `clear()` | Удалить точки останова Target, включая точки на fault handlers |

`boot`, `close`, `on_stop`, `report`, `owned`, `stops` и создание Target —
внутренний жизненный цикл агента. Вызовы GDB допустимы только в его основном
потоке. `-g3` сохраняет макросы, но не неиспользуемые функции и символы;
см. [HAL-макросы](HAL_MACRO_GUIDE.md) и [контракты](CONTRACTS.md).

## CLI

Из корня checkout модуля (из другой папки — по абсолютному пути `stm32_gdbtest/cli.py`):

```powershell
python -B -m stm32_gdbtest --version
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/Tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/Tests/board --requirements examples/minimal-consumer/profile/Tests/requirements.md
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
