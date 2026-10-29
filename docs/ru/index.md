# Документация stm32-gdbtest

Документация · [English](../en/index.md)

stm32-gdbtest — реализация [DDTT](DDTT.md) для STM32: сценарии в репозитории проекта проверяют
работающую прошивку на реальной плате через GDB и SWD-отладчик. Введение — [README](../../README.md),
требования — [ТЗ](../TECHNICAL_SPECIFICATION.md) и [ТЗ API](../TECHNICAL_SPECIFICATION_API.md)
(только на русском). Навыки для ИИ-агентов и маршруты TTDD — [skills](../../skills/README.md).

## Начало работы

- [Начало работы](GETTING_STARTED.md) — требования, проверка без платы, подключение подмодулем.
- [Написание тестов](TEST_AUTHORING.md) — процесс для человека и ИИ-агента.
- [Шпаргалка сценариста](SCENARIO_CHECKLIST.md) — осмотр до запуска, перед изменением состояния и после опыта.
- [Пошаговый проход сценария](MANUAL_DEBUG.md) — `run --interactive`: точки останова и Debug Console в VS Code без ограничения по времени.
- [Схемы запуска](RUN_LAYOUTS.md) — размещение runner, GDB и отладчика, подтверждённые сочетания.
- [Профили MCU](MCU_PROFILES.md) — описание target.toml и проверенные платы.
- [Стенды](STANDS.md) — платы стендов: сводка и схематичный вид сверху.
- [Спецификация DDTT](DDTT.md) — метод: термины, принципы, требования к сценариям, стендам и инструментам.

## Сценарии и API

- [API, CLI и миграция](API.md) — CMake, декоратор `case`, Target API, `run`, переход с hwtest.
- [Справочник методов](api/index.md) — все методы Target с версиями появления и примерами.
- [Каталог техник TECH-001…026](TESTING_TECHNIQUES.md) — устойчивые приёмы со ссылками из сценариев, условия и восстановление.
- [Живое окно выполнения](LIVE_EXECUTION.md) — `async def`, `resume(sync=False)`, `await wait/halt`; контракт и миграция.
- [Наблюдатель VTOR/FPB](LIVE_OBSERVER.md) — нейтральный пример живого окна, эталон и очистка.
- [Регистры MMIO](MMIO.md) — известные ограничения и рекомендуемый маршрут проверки.
- [SVD](SVD.md) — описание периферии для `t.mmio`, захват в пакет и границы.
- [ELF/HAL-контракты](CONTRACTS.md) — офлайн-проверка функций, типов, enum и хешей исходников.
- [HAL-макросы](../guides/ru/HAL_MACRO_GUIDE.md) — выбор макросов, контекст и контракт макросов.
- [Переход к 0.5.0](MIGRATION_050.md) — порядок миграции потребителя на API 3.
- [Миграция примеров на CMSIS](../guides/ru/CMSIS_MIGRATION.md) — исходная база, пробелы F030 и приёмка.

Нейтральные примеры: [имитируемый вход: write и ret](../../tests/controlled-input/README.md) ·
[моделируемый GPIO](../../tests/modeled-gpio/README.md) · [буфер и повторное потребление](../../tests/buffer-consumption/README.md) ·
[C++-контекст](../../tests/cpp-context/README.md) · [C++, кэш и отложенная запись в Renode](../../tests/renode-cache/README.md) ·
[остаточное состояние и кольцо](../../tests/stateful-buffer/README.md) · [логическое время](../../tests/logical-time/README.md) ·
[счётчики и стоимость наблюдения](../../tests/counter-cost/README.md) · [совместный захват](../../tests/external-capture/README.md) ·
[импорт ROS1 bag](../../tests/rosbag-import/README.md) · [наблюдатель живого окна](../../tests/live-observer/README.md).

## Результаты, журнал и DDTT

- [Журналирование](JOURNALING.md) — источники, квоты, полнота, политики error/truncate.
- [Экспорт результатов](RESULTS.md) — индекс свидетельств, CSV/HTML и проверка целостности.
- [DDTT в VS Code](DDTT_COVERAGE.md) — раскраска исходников по свидетельствам проверок.
- [Переносимый DDTT](PORTABLE_DDTT.md) — публичный отчёт с привязкой к ревизии, без локальных данных.
- [Квалификация условий](DDTT_QUALIFICATION.md) — сырой исход отдельно от допуска и итоговой раскраски.
- [Метрики проверок](HARDWARE_METRICS.md) — как читать числа исходов и чем они не являются.

## Стенды, GDB-серверы и CI

- [GDB-серверы](../guides/ru/BACKENDS.md) — OpenOCD, ST-LINK GDB Server, J-Link, st-util: [OpenOCD](../guides/ru/backends/openocd.md) ·
  [ST-LINK GDB Server](../guides/ru/backends/stlink.md) · [J-Link](../guides/ru/backends/jlink.md) · [st-util](../guides/ru/backends/st-util.md).
- [Владение отладчиком](../guides/ru/DEBUGGER_OWNERSHIP.md) — межпроектная блокировка на Windows и Linux.
- [Linux-стенд](../guides/ru/LINUX_STAND.md) — окружение без root, USB, J-Link, удалённый GDB-сервер по SSH, WSL2.
- [Аппаратный CI](../guides/ru/HARDWARE_CI.md) — пакеты подготовленного запуска, self-hosted раннер, прогоны 24/7.
- [Стендовый цикл](STAND_LOOP.md) — конечный план из принятых пакетов, попытки, STOP и SKIP.
- [Проверка связей HIL](HIL_INSPECT.md) — HIL, backend и SVD без запуска инструментов.
- [Идентификация MCU](TARGET_IDENTITY.md) — DEV_ID и заводской размер Flash.
- [Образы и CRC](IMAGES.md) — секции ELF, BIN, полный образ и область проверки Flash.
- [Manifest](MANIFESTS.md) — метаданные совместимости и происхождения сборки.
- [Совместимые МК](../guides/ru/COMPATIBLE_MCU.md) — Cortex-M других производителей (AT32): профиль, CMSIS, сценарии.
- [Проверки и CI](../guides/ru/testing.md) — уровни CI, Docker-образ, аппаратная проверка CI-прошивок.
- [Локальный CI](../guides/ru/local-ci.md) — Docker и L6: снимок, volume, отчёты и восстановление стенда.

## Эмуляторы

- [Renode](../guides/ru/RENODE.md) — конфигурация, процесс на сценарий, ограничения модели.
- [QEMU](../guides/ru/QEMU.md) — конфигурация и ограничения.
- [Проверки Renode](../guides/ru/RENODE_PROBES.md) — короткие опыты на модели и их границы.

## Свидетельства по платам

Сводки: [принятый API и результаты](../evidence/ru/API_ACCEPTANCE.md) · [итоговая сверка пяти профилей CMSIS](../evidence/ru/CMSIS_ACCEPTANCE.md).

- **F030:** [база CMSIS](../evidence/ru/F030_CMSIS_BASELINE.md) · [TIM3/IRQ](../evidence/ru/F030_CMSIS_TIMER.md) · [ADC/DMA](../evidence/ru/F030_CMSIS_ADC_DMA.md) ·
  [единицы ADC](../evidence/ru/F030_CMSIS_ADC_UNITS.md) · [занятый ADC](../evidence/ru/F030_ADC_BUSY.md) · [Sleep/WFI](../evidence/ru/F030_CMSIS_SLEEP.md) ·
  [RTC](../evidence/ru/F030_CMSIS_RTC.md) · [RTC deadline](../evidence/ru/F030_RTC_DEADLINE.md) · [сверка HAL→CMSIS](../evidence/ru/F030_CMSIS_ACCEPTANCE.md) ·
  [HAL: GPIO/RCC](../evidence/ru/F030_HAL_GPIO_RCC.md) · [HAL-регрессия](../evidence/ru/F030_HAL_REGRESSION.md) · [аппаратная приёмка HAL](../evidence/ru/F030_HAL_VALIDATION.md).
- **F103:** [clocks/GPIO/SysTick/TIM2](../evidence/ru/F103_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/ru/F103_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/ru/F103_CMSIS_RTC_SLEEP.md).
- **F401:** [clocks/GPIO/SysTick/TIM2](../evidence/ru/F401_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/ru/F401_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/ru/F401_CMSIS_RTC_SLEEP.md).
- **F411:** [clocks/GPIO/SysTick/TIM2](../evidence/ru/F411_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/ru/F411_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/ru/F411_CMSIS_RTC_SLEEP.md).
- **F429:** [clocks/GPIO/SysTick/TIM2](../evidence/ru/F429_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/ru/F429_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/ru/F429_CMSIS_RTC_SLEEP.md).

Это исторические этапы приёмки: числа относятся к своим ревизиям, текущее состояние — в [STATUS](STATUS.md).

## Выпуски и сопровождение

- [Текущее состояние](STATUS.md) — версия, проверенный объём, стенды и ограничения.
- [Версии и релизы](VERSIONING.md) — SemVer, теги, переходы между выпусками.
- [Изменения между выпусками](RELEASE_CHANGES.md) — что меняется для пользователя и что сделать.
- [Описание выпуска 0.6.0](../releases/v0.6.0.md) · [матрица приёмки 0.6.0](../development/release-060-acceptance.md) ·
  [приёмка 0.5.0](../development/release-050-acceptance.md) · [CHANGELOG](../../CHANGELOG.md).
- [Сопровождение](../guides/ru/maintenance.md) — порядок работы, ветки, коммиты, двуязычная документация.
- [Памятка команд](../guides/ru/HOWTO.md) — git (включая `git land`), частые проблемы стенда, отладчиков и Docker.
- [Структура документации](../development/README.md) — разделы, обязательные переводы, оформление README.
- Планирование: [памятка](../../TODO.md) · [дорожная карта](../../ROADMAP.md) · [история](../archive/TODO_ARCHIVE.md) ·
  [AGENTS.md](../../AGENTS.md).
