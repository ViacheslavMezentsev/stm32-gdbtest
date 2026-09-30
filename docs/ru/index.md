# Документация stm32-gdbtest

Документация · [English](../en/index.md)

Введение — [README](../../README.md): реализация [DDTT](DDTT.md) для STM32 — проверки
работающей прошивки на реальной плате через GDB и SWD-отладчик сценариями в
репозитории проекта. Требования — [ТЗ](../TECHNICAL_SPECIFICATION.md)
(ведётся только на русском).

## Начало работы

- [Спецификация DDTT](DDTT.md) — метод тестирования через отладчик на целевом устройстве: термины, принципы, требования к сценариям, стендам и инструментам.

- [Начало работы](GETTING_STARTED.md) — требования, проверка без платы, подключение подмодулем.
- [Написание тестов](TEST_AUTHORING.md) — процесс для человека и ИИ-агента.
- [API, CLI и миграция](API.md) — CMake, декоратор `case`, Target API, `run`, переход с hwtest.

## Механизмы

- [ELF/HAL-контракты](CONTRACTS.md) — offline-проверка функций, типов, enum и хэшей исходников.
- [HAL-макросы](HAL_MACRO_GUIDE.md) — выбор макросов, контекст и контракт макросов.
- [Образы и CRC](IMAGES.md) — секции ELF, BIN, полный образ и CRC-32/ISO-HDLC.
- [Manifest](MANIFESTS.md) — метаданные среды выполнения и происхождения сборки.
- [GDB-серверы](BACKENDS.md) — OpenOCD, ST-LINK GDB Server, J-Link; стенд.
- [Identity и Flash](TARGET_IDENTITY.md) — DEV_ID и заводской размер Flash.
- [Владение отладчиком](DEBUGGER_OWNERSHIP.md) — межпроектная блокировка на Windows и Linux.
- [Linux-стенд](LINUX_STAND.md) — окружение без root (Ubuntu 20.04, Orange Pi 5), USB, J-Link, удалённый GDB-сервер по SSH, WSL2.
- [Аппаратный CI](HARDWARE_CI.md) — пакеты подготовленного запуска, self-hosted раннер на Orange Pi, прогоны 24/7.

## Состояние и сопровождение

- [База CMSIS F030](F030_CMSIS_BASELINE.md) — четыре аппаратных сценария и ограничения.

- [Миграция примеров на CMSIS](CMSIS_MIGRATION.md) — исходная база, пробелы F030 и приёмка.

- [Текущее состояние](STATUS.md) — проверенный объём, стенды и ограничения.
- [Проверки и CI](testing.md) — уровни CI, Docker-образ, аппаратная проверка CI-прошивок.
- [Версии и релизы](VERSIONING.md) — SemVer, теги, подготовка релиза.
- [Сопровождение](maintenance.md) — порядок работы, ветки, коммиты, двуязычная документация.
- [Памятка](HOWTO.md) — команды git (включая `git land`), частые проблемы стенда, отладчиков и Docker, возврат состояния.
- [CHANGELOG](../../CHANGELOG.md), [дорожная карта](../../TODO.md), [AGENTS.md](../../AGENTS.md).

[F030 CMSIS: TIM3/IRQ](F030_CMSIS_TIMER.md).

ADC/DMA F030: сырые отсчёты и timeout, API ядра без изменений. [ADC/DMA](F030_CMSIS_ADC_DMA.md).

F030: преобразование ADC и численные сценарии, API ядра без изменений. [ADC units](F030_CMSIS_ADC_UNITS.md).

F030 Sleep/WFI: профильные сценарии через GDB unwind, API ядра не меняется. [Sleep evidence](F030_CMSIS_SLEEP.md).

F030 RTC: Alarm A на LSI, 16/16 HW PASS, HAL восстановлен. API ядра без изменений. [RTC](F030_CMSIS_RTC.md).

F030: проверка занятого ADC, API без изменений. [Протокол](F030_ADC_BUSY.md).

F030: RTC deadline через инъекцию аргумента, API без изменений. [Протокол](F030_RTC_DEADLINE.md).

[Сверка HAL→CMSIS F030 и порядок пакета веток](F030_CMSIS_ACCEPTANCE.md).

- [F030 HAL regression: план переноса и приёмка](F030_HAL_REGRESSION.md).
