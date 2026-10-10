# stm32-gdbtest

[![Docs](https://img.shields.io/github/actions/workflow/status/ViacheslavMezentsev/stm32-gdbtest/docs.yml?branch=main&label=Docs&style=flat-square)](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/workflows/docs.yml)
[![Offline](https://img.shields.io/github/actions/workflow/status/ViacheslavMezentsev/stm32-gdbtest/offline.yml?branch=main&label=Offline&style=flat-square)](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/workflows/offline.yml)

[![Hardware campaign](https://img.shields.io/badge/Hardware-candidate%200.4.0%20SSH-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)
[![Board models tested](https://img.shields.io/badge/Boards%20tested-5-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)
[![Recorded hardware cases](https://img.shields.io/badge/HW%20cases%20%28recorded%29-233-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)
[![Latest recorded hardware verification](https://img.shields.io/badge/HW%20verified%20%28latest%29-2026--10--10-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)

[English](README.en.md)

**stm32-gdbtest — реализация [DDTT](docs/ru/DDTT.md) для STM32: проверки работающей
прошивки на реальной плате через GDB и SWD-отладчик, оформленные сценариями в
репозитории проекта.** Сценарий пишет разработчик или ИИ-агент; он выполняется в GDB
на компьютере, управляет прошивкой через отладочный сервер и даёт отчёт JSON/JUnit.
Тестового кода в прошивке нет. Один и тот же сценарий запускается вручную, из CTest,
в раннере CI или в цикле на стенде — при любой схеме подключения: отладчик у рабочего
компьютера, на Linux-стенде вроде Orange Pi или на удалённом стенде по SSH.

DDTT (debugger-driven testing on target, тестирование через отладчик на целевом
устройстве) — метод, описанный отдельной [спецификацией](docs/ru/DDTT.md); этот
репозиторий — его эталонная реализация. Это не симулятор MCU и не unit-test
фреймворк, запускающий тестовые функции внутри прошивки. Нужны собранный ELF с отладочной информацией, профиль MCU и стенд.

## Зачем нужен этот подход

Агент может проектировать изменение и сам работать с GDB, но проверку, выполненную
только в чате, трудно воспроизвести. Здесь действия и ожидания сохраняются
в репозитории как повторяемые тесты: требование →
сценарий в `tests/board` → проверка без оборудования (контракты ELF, образ) →
запуск на стенде → отчёт, который читает и агент, и человек. Сценарии остаются
тестовыми кейсами проекта и выполняются снова после каждого изменения — на любом
стенде из описанных, вручную или автоматически.

При работе со STM32 важно проверять не только вычисления, но и настройку
периферии, обработку прерываний и реакцию приложения на возвращаемые HAL коды состояния
(например, `HAL_ERROR`, `HAL_BUSY`, `HAL_TIMEOUT`). Многое из
этого разработчик уже проверяет вручную в отладчике; сценарий фиксирует такие
действия и ожидания.

Проект вырос из практических опытов GDB-Python на платах F1/F4. Инфраструктура
выделена из [стендового проекта](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill),
чтобы подключать её к другим приложениям, добавляя собственные профили и тесты.

Исторические видео автора **на русском языке**:

- [Ранние опыты тестирования через GDB-Python](https://www.youtube.com/watch?v=idlKlSHc0wU).
- [Модульное тестирование для малых встраиваемых систем (отладка py-тестов)](https://www.youtube.com/watch?v=_BuMmQGHol4) — показан прежний способ работы с Python-тестами.

Видео поясняют происхождение подхода; актуальный API и команды описаны в документации модуля.

## Как это работает

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
    I["ELF + профиль MCU + Python-тесты"] --> H["Host runner на ПК"]
    H --> A["GDB-Python: сценарий и Target API"]
    A <--> S["GDB-сервер"]
    S <--> D["ST-Link / J-Link"]
    D <-->|SWD| M["STM32 с прошивкой приложения"]
    A --> R["JSON / JUnit"]
    H --> R
```

Runner проверяет входные артефакты, запускает сервер и GDB, ограничивает время
выполнения и сохраняет результаты. Сценарий достигает нужной точки программы,
читает переменные, структуры и регистры, сравнивает их с ожиданиями. При необходимости
он может изменить значение, принудительно завершить функцию или вызвать функцию
прошивки, чтобы проверить реакцию вызывающего кода. Тестовая логика не добавляется в прошивку.

```python
from stm32_gdbtest import case, within


# Verify the system clock and the SysTick period after start-up.
@case("HW_CLOCK", contracts=("clock_macros",))
def clock(t):
    t.reach("board_led_toggle")

    # A string cell is a GDB expression; numbers and matchers are Python values.
    t.check([
        ("HSI enabled and ready", "RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)", "RCC_CR_HSION | RCC_CR_HSIRDY"),
        ("1 ms SysTick at 8 MHz", "SysTick->LOAD", 8_000_000 // 1000 - 1),
        ("VDDA is plausible", "board_adc_reading.vdda_mv", within(2800, 3600))
    ])
```

## Возможности

- Запуск сценариев через OpenOCD, ST-LINK GDB Server, st-util и J-Link GDB Server; runner и GDB
  на Windows или Linux, GDB-сервер рядом с ними или на Linux-хосте стенда по SSH.
- Проверка и запись образа: по загружаемым секциям ELF или полный образ с заполнением
  и CRC-32 на ПК ([образы и CRC](docs/ru/IMAGES.md)); проверка DEV_ID и размера Flash
  в режимах `warn` и `strict` ([identity](docs/ru/TARGET_IDENTITY.md)).
- Target API кандидата 0.4.0 ([справочник](docs/ru/api/index.md), [API](docs/ru/API.md)): навигация `reach`, `step`,
  `until`, `finish`, точки `Point` и `watch`; чтение и запись `read`/`write` (в том числе таблицей записей),
  `evaluate`, `memory`, `symbol`, `registers`, `frames`, `locals`; инъекции `ret` и `call`; одна `check`
  с сопоставителями и таблицей, ожидаемый отказ `refused`; профиль прогона `profile` с данными проекта и
  сведениями о сборке; журнал `record`/`records`, завершение неприменимого сценария `skip(reason)`.
  Прежние `value`/`fields`/`set_value`/`force_return` удалены; [миграция](docs/ru/RELEASE040_SCOPE.md#2-очистка-сценариев-и-документации).
  Приёмы — в [каталоге техник](docs/ru/TESTING_TECHNIQUES.md).
- Проверки без оборудования: build manifest, выборочные ELF/HAL-контракты,
  `run --prepare-only`, трассировка требований; на них основан CI
  ([проверки и CI](docs/ru/testing.md)).
- Таймауты с попыткой восстановления, блокировка отладчика между процессами,
  отчёты JSON/JUnit, интеграция с CMake/CTest.
- Пакеты подготовленного запуска (`pack`, `run --package`): сборка в одном месте,
  запуск на стенде; аппаратный CI на self-hosted раннере ([аппаратный CI](docs/ru/HARDWARE_CI.md)).

## Ограничения

- **Нужен опыт ручной работы с GDB.** Автор должен понимать, где остановить
  программу, какой стековый кадр (frame) выбран, что делают `step`, `finish`,
  reset и принудительный возврат (`ret`). Сценарий автоматизирует эти действия;
  модуль не выбирает правильные точки наблюдения и ожидания за разработчика.
- **Сценарий написан на Python, а выражения вычисляет GDB.** Чтение C/C++-выражений
  через `gdb.parse_and_eval` или Target API не превращает сценарий в произвольный
  C-код. В частности, statement-макрос `do { ... } while (0)` не является
  вычисляемым выражением. Вызов функции из выражения исполняет код на MCU и может
  изменить состояние или зависнуть; чтение MMIO тоже может иметь побочный эффект.
- **Доступность данных зависит от ELF и текущего контекста.** `-g3` сохраняет
  определения макросов, но не возвращает удалённые оптимизатором переменные,
  типы и функции. Для HAL/CMSIS-макроса нужна исходная позиция в единице компиляции,
  где он определён; после перехода в другую функцию или смены frame он может
  стать недоступен. Контракт проверяет наличие и раскрытие макроса, но не
  безопасность его вычисления на плате. См. [макросы](docs/ru/HAL_MACRO_GUIDE.md)
  и [техники тестирования](docs/ru/TESTING_TECHNIQUES.md).
- **Отладка меняет поведение системы.** Остановки, reset и инъекции влияют на
  время и IRQ; периферия при halt может продолжать работать. Проверка Sleep/WFI
  не измеряет потребление. Число hardware breakpoints ограничено MCU;
  оптимизация и backend влияют на достижимость точки и работу `finish`/`ret`. Точка наблюдения
  на Cortex-M0 останавливает ядро на одну-две инструкции позже записи.
- **Нужен исправный и согласованный стенд.** Потеря USB/SWD или зависший сервер
  могут потребовать ручного переподключения; timeout/recovery не гарантирует
  физического восстановления связи. Такой случай сохранён в [приёмке rc.2](docs/ru/RC2_READINESS.md).
  Поддержка проверяется для конкретного сочетания MCU, сборки, GDB и backend.
- **Результат ограничен условиями сценария.** Инъекция кода возврата HAL проверяет
  ветвь приложения, но не воспроизводит физическую причину ошибки периферии.
  Модуль не заменяет измерительные приборы и не вычисляет покрытие автоматически;
  PASS не означает проверку всей HAL или всех режимов устройства.

## Схемы запуска

Сценарий и отчёт одинаковы во всех схемах; меняется только файл локального стенда
(`*.local.toml`, `remote.toml`), который остаётся у пользователя.

| Схема | Runner и GDB | GDB-сервер и отладчик | Проверка новых сценариев 0.4.0 |
| --- | --- | --- | --- |
| Локально на Windows | Windows | тот же компьютер, st-util 1.9.0 | 5 плат: 20 PASS + 5 SKIP |
| Локально на Linux-стенде | Orange Pi 5, Ubuntu 20.04 aarch64 | тот же компьютер, st-util 1.9.0 | 5 плат: 20 PASS + 5 SKIP, запуск через GitHub |
| Удалённый сервер с Windows | Windows | Orange Pi 5 по SSH, st-util 1.9.0 | 5 плат: 20 PASS + 5 SKIP |
| Удалённый сервер из WSL2 | WSL2, Ubuntu 20.04 x86_64 | Orange Pi 5 по SSH, st-util 1.9.0 | 5 плат: 20 PASS + 5 SKIP |
| Пакет подготовленного запуска | пакет собран отдельно, runner на месте запуска | Windows или Orange Pi 5 | проверен в локальных и SSH-схемах выше |
| Аппаратный CI | prepare на GitHub, runner/GDB на Orange Pi 5 | тот же Orange Pi, без SSH между runner и сервером | Hardware №13: 20 PASS + 5 SKIP |
| Локально на Linux x86_64 | Linux-ПК | тот же компьютер | на оборудовании не проверялось |
| WSL2 с USB-пробросом | WSL2 | USB через usbipd-win | на оборудовании не проверялось |

Строки «локально на Linux» и «аппаратный CI» описывают один прогон, а не две кампании.
На каждой плате выполнены четыре новых сценария и отдельный вариант ожидаемого SKIP.
Это выборочный набор, не повтор всей приёмки API. Версии, SHA, исходные ошибки и ограничения —
[протоколы 0.4.0](docs/ru/API040_SCENARIOS.md). Полные кампании 0.3.0 (218 сочетаний профиль/сценарий)
и 0.4.0 SSH (233), а также десятиэтапный lifecycle сохранены в [матрице приёмки](docs/ru/API_ACCEPTANCE.md).

### Локальный запуск: Windows или Linux

Runner, GDB-Python и сервер работают на одном компьютере. Это схема Windows
и Orange Pi; локальный Linux x86_64 пока не проверен на оборудовании.

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
    subgraph PC["Компьютер: Windows / Linux"]
        R["Runner + GDB-Python"] <--> S["GDB-сервер"]
        R --> O["Отчёт"]
    end
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### Удалённый сервер: Windows или WSL2 → Linux-стенд

Runner и сценарий работают на рабочем ПК; SSH запускает сервер на стенде
и передаёт соединение GDB через туннель. Отладчик физически подключён к стенду.

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
    R["Windows / WSL2: runner + GDB-Python"] <-->|SSH tunnel| S["Linux-стенд: GDB-сервер"]
    R --> O["Отчёт"]
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### Пакет: сборка отдельно от запуска

На компьютер стенда передаётся пакет с ELF, профилем и сценариями.
`run --package` запускает там и GDB-Python, и сервер; отчёты сохраняются там же.

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
    B["Windows / GitHub: сборка + pack"] --> P["Пакет"]
    P --> R["Linux-стенд: run --package + GDB-Python"]
    R --> O["Отчёт"]
    R <--> S["GDB-сервер"]
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### Аппаратный CI: GitHub и self-hosted раннер

GitHub-hosted job собирает и проверяет пакет без платы. Self-hosted job
на Orange Pi скачивает пакет, запускает аппаратную проверку и загружает отчёты.

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
    G["GitHub: build + prepare + pack"] --> A["Артефакт пакета"]
    A --> R["Orange Pi: self-hosted runner + GDB-Python"]
    R --> O["GitHub: отчёты"]
    R <--> S["GDB-сервер"]
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### WSL2 с USB-пробросом: аппаратно не проверено

Все процессы тестирования работают в WSL2; Windows передаёт USB-устройство
в Linux через usbipd-win. Это отдельный, пока не проверенный на платах вариант.

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
    W["WSL2: runner + GDB-Python + сервер"] <-->|usbipd-win| D["Отладчик: USB Windows"]
    W --> O["Отчёт"]
    D <-->|SWD| M["STM32"]
```

Удалённый режим работает только по ключам SSH; блокировка отладчика действует на
хосте стенда, связь контролируется сигналом присутствия. ST-LINK GDB Server на
Linux aarch64 недоступен (ST не выпускает его для arm64), поэтому на Orange Pi
используются OpenOCD, J-Link и st-util. Подробности: [Linux-стенд](docs/ru/LINUX_STAND.md),
[GDB-серверы](docs/ru/BACKENDS.md).

**Как читать счётчики.** Бейдж кандидата описывает сохранённый полный SSH-прогон 0.4.0:
пять STM32, 233 сочетания «профиль + сценарий», дата 10.10.2026. Он не суммирует новые выборочные
прогоны и не подтверждает финальный SHA или все backend. Бейджи статические, не процент покрытия.
Границы и прежние срезы — в [описании метрик](docs/ru/HARDWARE_METRICS.md).

## Профили MCU

Профиль — файл `target.toml` с описанием конкретного MCU: Flash, DEV_ID, число
hardware breakpoints, обработчики отказов, диагностические регистры, цель OpenOCD.
Готовой библиотеки профилей «для любого STM32» в модуле нет: профиль пишет
потребитель под свою плату, взяв за образец один из имеющихся. Несколько вариантов
MCU одной прошивки могут делить сценарии, каждый со своим профилем (`PROFILE`).

Образцы в репозитории: CI-прошивки `tests/firmware/profiles/` (F030R8, F103C8, F401CC,
F411CE, F429ZI — Cortex-M0, M3, M4; AT32F403A — совместимый Cortex-M4) и пример
`examples/minimal-consumer/profile/` (F411CE).

| MCU | Отладчик / GDB-сервер | Где проверено |
| --- | --- | --- |
| STM32F030R8 | ST-Link (NUCLEO) / OpenOCD, st-util; J-Link GDB Server | CI-прошивка, HAL-фикстура, стендовый проект |
| STM32F103C8 | J-Link / J-Link GDB Server; ST-Link / st-util | CI-прошивка, стендовый проект |
| STM32F103CB | J-Link CE / J-Link GDB Server | демонстрационный проект [stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) |
| STM32F401CC | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI-прошивка, стендовый проект |
| STM32F411CE | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI-прошивка, пример, стендовый проект |
| STM32F429ZI | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI-прошивка, стендовый проект |
| STM32G474CE | ST-Link / OpenOCD на Orange Pi 5 | проект потребителя (Arduino Core STM32) |
| AT32F403ACGU7 (Artery) | J-Link / J-Link GDB Server; ST-Link / st-util | CI-прошивка, после 0.3.0 |

Для OpenOCD, ST-LINK GDB Server и st-util достаточно профиля. J-Link GDB Server требует
имени устройства: оно задаётся в профиле (`jlink_device`), а для STM32F103C8T6,
STM32F030R8T6 и STM32F103CBT6 известно модулю. H503 не поддержан. Поддержка определяется конкретной
комбинацией MCU, HAL, GDB и backend, а не семейством: [текущее состояние](docs/ru/STATUS.md).

**Совместимые МК других производителей.** Модуль не привязан к ST: нужны ядро Cortex-M и
GDB-сервер, который подключается к кристаллу. Такой МК (Artery AT32, GigaDevice GD32, Geehy APM32
и т. п.) подключается своим профилем и CMSIS производителя, без изменений модуля. Проверен пока один —
AT32F403ACGU7 на WeAct AT32F4 Core Board через J-Link; он не входит в аппаратную кампанию 0.3.0
и в счётчики выше. Профиль, SDK, особенности сценариев и порядок подключения своего МК —
в [совместимых МК](docs/ru/COMPATIBLE_MCU.md). Каждый новый кристалл требует своей приёмки на плате.

## Состояние

Опубликованный пакет — **0.3.0**. В этой ветке готовится **stm32-gdbtest 0.4.0**:
`API_VERSION=2`, target schema 2, [ТЗ API](docs/TECHNICAL_SPECIFICATION_API.md) 0.3.16,
[общее ТЗ](docs/TECHNICAL_SPECIFICATION.md) 0.93. Это версии пакета и контрактов, не версия Python.
Удалены `value`, `fields`, `set_value`, `force_return`; добавлены сопоставители, SKIP, захват records
и внешняя обработка результатов. Миграция — [API](docs/ru/API.md), состав и ограничения —
[граница выпуска](docs/ru/RELEASE040_SCOPE.md), история — [CHANGELOG](CHANGELOG.md).

Аппаратные протоколы сохранены; публикация кандидата и CI окончательного SHA ещё не подтверждены.
В частности, ограничения ST-LINK GDB Server остаются явными. Ближайшие шаги — [TODO](TODO.md).

## Состав и зависимости

- `stm32_gdbtest/` — runner, GDB-агент, Target API, backend, контракты и CMake-интеграция.
- `tests/host`, `tests/fixtures` — проверки инфраструктуры без платы.
- `tests/firmware`, `ci/` — CI-прошивки F030R8/F103C8/F401CC/F411CE/F429ZI/AT32F403A, Docker-образ, сценарий
  проверок и `run_hw.py` для аппаратной проверки на стенде; `tests/firmware/common/tests` — общие
  сценарии всех профилей, включая девять сценариев-примеров API.
- `tests/hal-f030/` — самостоятельная HAL-регрессия F030, CI и аппаратная приёмка.
- `tools/stand_loop.py` — [конечные автономные циклы](docs/ru/STAND_LOOP.md) из пакетов и артефакты для агента.
- `tools/linux_stand.py` — установка окружения Linux-стенда без root.
- `examples/minimal-consumer/` — самостоятельный пример прошивки и теста для F411.
- `docs/ru`, `docs/en` — подключение, написание сценариев и описание механизмов;
  `docs/TECHNICAL_SPECIFICATION.md` — ТЗ.

Нужны host Python 3.11+, ARM GCC и GDB со встроенным Python 3.11+, CMake 3.25+ и Ninja,
SWD-отладчик и его GDB-сервер, библиотеки прошивки. HAL/CMSIS, Cube-пакеты и vendor
tools в модуль не входят. GDB-Python — отдельный интерпретатор, не окружение Python
вашего ПК. Linux-стенд: glibc ≥ 2.31 (Ubuntu 20.04 и новее), x86_64 или aarch64.

Модуль подключается как **Git-подмодуль** (или отдельный клон, путь к которому задаёт
`STM32_GDBTEST_SOURCE_DIR`). Настройки MCU, тесты приложения и локальный стенд остаются
у потребителя. Начните с [подключения и примера](docs/ru/GETTING_STARTED.md), затем
перейдите к [написанию тестов](docs/ru/TEST_AUTHORING.md) — вручную или с помощью агента. Агенту —
[навыки](skills/README.md) `stm32-gdbtest-integrate`, `stm32-gdbtest-scenarios`, `stm32-gdbtest-run` и `stm32-gdbtest-results`.

## Документация и связанные проекты

- [Карта документации](docs/ru/index.md), [ТЗ](docs/TECHNICAL_SPECIFICATION.md), [ТЗ API](docs/TECHNICAL_SPECIFICATION_API.md), [принятые результаты](docs/ru/API_ACCEPTANCE.md).
- [API и CMake/CLI](docs/ru/API.md), [справочник методов](docs/ru/api/index.md), [каталог техник и стиль сценариев](docs/ru/TESTING_TECHNIQUES.md), [ELF/HAL-контракты](docs/ru/CONTRACTS.md), [HAL-макросы](docs/ru/HAL_MACRO_GUIDE.md).
- [Экспорт, целостность и HTML](docs/ru/RESULTS.md), [навык интерпретации результатов](skills/stm32-gdbtest-results/SKILL.md).
- [GDB-серверы](docs/ru/BACKENDS.md), [identity и Flash](docs/ru/TARGET_IDENTITY.md), [владение отладчиком](docs/ru/DEBUGGER_OWNERSHIP.md), [manifest](docs/ru/MANIFESTS.md), [образы ELF/BIN и CRC](docs/ru/IMAGES.md).
- [Текущее состояние](docs/ru/STATUS.md), [проверки и CI](docs/ru/testing.md), [версии](docs/ru/VERSIONING.md), [планы](TODO.md), [изменения](CHANGELOG.md).
- [stm32-hwtest-blackpill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill) — прошивки, аппаратные проверки, общая архитектура и практика применения.
- [stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml) — связанный проект сборки STM32; для работы модуля он не обязателен.

Лицензия — [MIT](LICENSE). [Происхождение](SOURCE.md), [правила для разработчиков и агентов](AGENTS.md), [сопровождение](docs/ru/maintenance.md).

[Выпуск v0.3.0](docs/releases/v0.3.0.md), [подготовка и миграция v0.2.0-rc.1](docs/ru/RC020_READINESS.md).
