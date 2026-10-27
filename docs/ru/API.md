# API, CLI и подключение

[Документация](index.md) · [English](../en/API.md)

Документ описывает **0.5.x / API_VERSION=3**. Контракты операций и границы поддержки —
в [справочнике](api/index.md), изменения для пользователей — в [истории переходов](RELEASE_CHANGES.md).

## Конфигурация и исполнение

Предпочтительный вход — `SESSION_CONFIG` в CMake и `[config]` в session.toml:
`target`, `api`, `image`, `[mmio].svd` и `[data]` выбираются явно по своим контрактам.
[Структура HIL и пути](HIL_INSPECT.md), [inspect](HIL_INSPECT.md), [SVD](SVD.md).
Если SESSION_CONFIG выбран, не смешивайте его с PROFILE и отдельной image policy.
`t.profile` предоставляет неизменяемые данные и происхождение; `record`/`records` — журнал
одного сценария. Для сохранения в файл включите `[results] capture = true`.
[Результаты и экспорт](RESULTS.md) проверяются отдельно от исхода сценария.

Обычный `def` использует синхронные навигацию и `call`. В `async def` они требуют `await`;
`resume(sync=False)` запускает живое окно, `await wait()` ждёт, `await halt()` останавливает.
Данные доступны только при подтверждённой остановке. `ret` и методы данных немедленны;
`execute` в async запрещён. [Полный контракт](LIVE_EXECUTION.md).

Для периферии используйте `t.mmio.read/write` и SVD. Обычный `write` — не безопасная
замена MMIO; скрытые вызовы функций в выражениях данных запрещены. [MMIO](MMIO.md).
`memory` требует полный ответ, `write` вычисляет RHS один раз; ни один метод не откатывает
все побочные эффекты. C++ preflight не расширяет допустимые имена `call`.

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

## Миграция A1 к 0.6.0

API_VERSION остаётся 3. `reason` MMIO теперь можно использовать без override.
Первичная ошибка исполнения/транспорта не заменяется отказом аудита; отдельные
диагностики и подтверждение cleanup описаны в [resume](api/resume.md),
[MMIO](api/mmio.md) и [RecordError](api/record-error.md). После успешного исполнения
отказ записи execution теперь ApiError/journal_unavailable, а не голый RecordError.
Лимиты, capture и формат записей не изменены; увеличивать их для сокрытия ошибки не нужно.
