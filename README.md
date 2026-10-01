# stm32-gdbtest

[![Docs](https://img.shields.io/github/actions/workflow/status/ViacheslavMezentsev/stm32-gdbtest/docs.yml?branch=main&label=Docs&style=flat-square)](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/workflows/docs.yml)
[![Offline](https://img.shields.io/github/actions/workflow/status/ViacheslavMezentsev/stm32-gdbtest/offline.yml?branch=main&label=Offline&style=flat-square)](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/workflows/offline.yml)

[![Hardware evidence](https://img.shields.io/badge/Hardware-historical%20snapshot-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)
[![Board models tested](https://img.shields.io/badge/Boards%20tested-4-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)
[![Recorded hardware cases](https://img.shields.io/badge/HW%20cases%20%28recorded%29-73-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)
[![Latest recorded hardware verification](https://img.shields.io/badge/HW%20verified%20%28latest%29-2026--10--01-blue?style=flat-square)](docs/ru/HARDWARE_METRICS.md)

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
он может изменить значение или принудительно завершить функцию для проверки
реакции вызывающего кода. Тестовая логика не добавляется в прошивку.

## Возможности

- Запуск сценариев через OpenOCD, ST-LINK GDB Server и J-Link GDB Server; runner и GDB
  на Windows или Linux, GDB-сервер рядом с ними или на Linux-хосте стенда по SSH.
- Проверка и запись образа: по загружаемым секциям ELF или полный образ с заполнением
  и CRC-32 на ПК ([образы и CRC](docs/ru/IMAGES.md)); проверка DEV_ID и размера Flash
  в режимах `warn` и `strict` ([identity](docs/ru/TARGET_IDENTITY.md)).
- Target API: hardware breakpoints, `reach` с проверкой кадра, чтение значений и
  структур, `set_value` и `force_return` для инъекций ([API](docs/ru/API.md)).
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
  reset и принудительный возврат. Сценарий автоматизирует эти действия;
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
  оптимизация и backend влияют на достижимость точки и работу `finish`/`force_return`.
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

| Схема | Runner и GDB | GDB-сервер и отладчик | Состояние |
| --- | --- | --- | --- |
| Локально на Windows | Windows | тот же компьютер | проверено: 4 стенда |
| Локально на Linux-стенде | Orange Pi 5, Ubuntu 20.04 aarch64 | тот же компьютер | проверено: 3 стенда |
| Удалённый сервер с Windows | Windows | Orange Pi 5 по SSH (`[remote]`) | проверено: 3 стенда и проект потребителя |
| Удалённый сервер из WSL2 | WSL2, Ubuntu 20.04 x86_64 | Orange Pi 5 по SSH | проверено: 3 стенда |
| Пакет подготовленного запуска | сборка на Windows или в GitHub Actions | Orange Pi 5, `run --package` | проверено: 3 стенда |
| Аппаратный CI | prepare на GitHub, hardware на self-hosted раннере | Orange Pi 5 (служба раннера) | проверено: 3 стенда |
| Локально на Linux x86_64 | Linux-ПК | тот же компьютер | реализовано, на оборудовании не проверялось |
| WSL2 с отладчиком через usbipd-win | WSL2 | тот же компьютер | реализовано как Linux, не проверялось |

### Локальный запуск: Windows или Linux

Runner, GDB-Python и сервер работают на одном компьютере. Это схема Windows
и Orange Pi; локальный Linux x86_64 пока не проверен на оборудовании.

```mermaid
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
flowchart LR
    W["WSL2: runner + GDB-Python + сервер"] <-->|usbipd-win| D["Отладчик: USB Windows"]
    W --> O["Отчёт"]
    D <-->|SWD| M["STM32"]
```

Удалённый режим работает только по ключам SSH; блокировка отладчика действует на
хосте стенда, связь контролируется сигналом присутствия. ST-LINK GDB Server на
Linux aarch64 недоступен (ST не выпускает его для arm64), поэтому на Orange Pi
используются OpenOCD и J-Link. Подробности: [Linux-стенд](docs/ru/LINUX_STAND.md),
[GDB-серверы](docs/ru/BACKENDS.md).

**Как читать счётчики.** `Hardware: historical snapshot`, `Boards tested` и `HW cases (recorded)` описывают сохранённые аппаратные протоколы CMSIS-примеров: четыре модели плат и 73 уникальных сочетаний «профиль + fixture + сценарий». Повторы и сборки не увеличивают это число; `HW verified (latest)` — дата самого нового включённого опыта. Это исторический срез разных ревизий, а не единый прогон текущего main и не процент покрытия. Состав, границы и результаты приведены в [описании метрик и таблице проверок](docs/ru/HARDWARE_METRICS.md).

## Профили MCU

Профиль — файл `target.toml` с описанием конкретного MCU: Flash, DEV_ID, число
hardware breakpoints, обработчики отказов, диагностические регистры, цель OpenOCD.
Готовой библиотеки профилей «для любого STM32» в модуле нет: профиль пишет
потребитель под свою плату, взяв за образец один из имеющихся. Несколько вариантов
MCU одной прошивки могут делить сценарии, каждый со своим профилем (`PROFILE`).

Образцы в репозитории: CI-прошивки `tests/firmware/profiles/` (F030R8, F103C8, F401CC,
F411CE — Cortex-M0, M3, M4) и пример `examples/minimal-consumer/profile/` (F411CE).

| MCU | Отладчик / GDB-сервер | Где проверено |
| --- | --- | --- |
| STM32F030R8 | J-Link STLink / J-Link GDB Server | CI-прошивка, стендовый проект |
| STM32F103C8 | J-Link CE / J-Link GDB Server | CI-прошивка, стендовый проект |
| STM32F103CB | J-Link CE / J-Link GDB Server | демонстрационный проект [stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) |
| STM32F401CC | ST-Link / OpenOCD | [CMSIS: 15 сценариев](docs/ru/F401_CMSIS_ADC_DMA.md) |
| STM32F411CE | ST-Link / OpenOCD и ST-LINK GDB Server | CI-прошивка, пример, стендовый проект |
| STM32F429ZI | ST-Link / OpenOCD и ST-LINK GDB Server | стендовый проект |
| STM32F401CC | ST-Link / ST-LINK GDB Server | стендовый проект, ранние проверки |
| STM32G474CE | ST-Link / OpenOCD на Orange Pi 5 | проект потребителя (Arduino Core STM32) |

Для OpenOCD и ST-LINK GDB Server достаточно профиля. J-Link GDB Server требует
соответствия имени устройства; сейчас оно есть для STM32F103C8T6, STM32F030R8T6 и
STM32F103CBT6. H503 не поддержан. Поддержка определяется конкретной
комбинацией MCU, HAL, GDB и backend, а не семейством: [текущее состояние](docs/ru/STATUS.md).

## Состояние

Опубликован **0.1.0-rc.2**: [приёмка и ограничения](docs/ru/RC2_READINESS.md).
После rc.1 исправлены manifest и HAL macro contracts, расширен CMSIS F030,
добавлена самостоятельная HAL F030-регрессия. В rc.2 F103/F411 сохраняют базовые
boot/GPIO-сценарии. Точный проверенный объём и ограничения — [STATUS](docs/ru/STATUS.md).
В выпускной ветке версия Python — `0.1.0rc2`, `API_VERSION = 1`.
Ветка после rc.2 расширяет F103: clocks/GPIO/SysTick/TIM2/ADC/DMA, 15 сценариев;
[протокол](docs/ru/F103_CMSIS_ADC_DMA.md). Опубликованный тег неизменен.

RISC-V, полный перенос остальных примеров, управление внешним оборудованием,
надзор за дочерними процессами и Python-упаковка остаются в [дорожной карте](TODO.md).

## Состав и зависимости

- `stm32_gdbtest/` — runner, GDB-агент, Target API, backend, контракты и CMake-интеграция.
- `tests/host`, `tests/fixtures` — проверки инфраструктуры без платы.
- `tests/firmware`, `ci/` — CI-прошивки F030R8/F103C8/F411CE, Docker-образ, сценарий
  проверок и `run_hw.py` для аппаратной проверки на стенде.
- `tests/hal-f030/` — самостоятельная HAL-регрессия F030, CI и аппаратная приёмка.
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
перейдите к [написанию тестов](docs/ru/TEST_AUTHORING.md) — вручную или с помощью агента.

## Документация и связанные проекты

- [Карта документации](docs/ru/index.md), [ТЗ](docs/TECHNICAL_SPECIFICATION.md).
- [API и CMake/CLI](docs/ru/API.md), [ELF/HAL-контракты](docs/ru/CONTRACTS.md), [HAL-макросы](docs/ru/HAL_MACRO_GUIDE.md).
- [GDB-серверы](docs/ru/BACKENDS.md), [identity и Flash](docs/ru/TARGET_IDENTITY.md), [владение отладчиком](docs/ru/DEBUGGER_OWNERSHIP.md), [manifest](docs/ru/MANIFESTS.md), [образы ELF/BIN и CRC](docs/ru/IMAGES.md).
- [Текущее состояние](docs/ru/STATUS.md), [проверки и CI](docs/ru/testing.md), [версии](docs/ru/VERSIONING.md), [планы](TODO.md), [изменения](CHANGELOG.md).
- [stm32-hwtest-blackpill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill) — прошивки, аппаратные проверки, общая архитектура и практика применения.
- [stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml) — связанный проект сборки STM32; для работы модуля он не обязателен.

Лицензия — [MIT](LICENSE). [Происхождение](SOURCE.md), [правила для разработчиков и агентов](AGENTS.md), [сопровождение](docs/ru/maintenance.md).
