# Документация stm32-gdbtest

Документация · [English](../en/index.md)

[R8: бюджет точек по коду](RC3_API_R8.md): шесть слотов, fault guards, резерв finish и продолжение без reset.

[R7: диапазоны и бюджет watchpoints](RC3_API_R7.md): выравнивание, исчерпание точек, восстановление и точное разбиение.

[R6: стек и рекурсивные кадры](RC3_API_R6.md): выбор контекста, FinishBreakpoint и адресная подмена результата.

[R5: типы возврата и ABI](RC3_API_R5.md): uint64/float/struct; ограничение return структуры и проверка возвратного буфера.

[R4: выходные буферы и подмена результата](RC3_API_R4.md): естественный вызов, полный пакет, ошибка и короткий ответ.

[R3: действия при остановке и счётчики](RC3_API_R3.md): 32/32 F411 native DAP; команды, переполнение, same-value writes.

[R2: навигация, вызовы и watchpoints](RC3_API_R2.md): 56/56 HLA и 8/8 native DAP; перенос в ядро только после утверждения владельца.

[Первые аппаратные опыты R1](RC3_API_R1.md): F411, GDB14/16, 48/48 и проверки отказов.

Подготовка rc3: [исследование GDB Python API и план аппаратных экспериментов](RC3_API_RESEARCH.md). Методы пока не реализованы.

[F429 RTC/Sleep/deadline/recovery:20/20 HW +5 повторов, внешний timeout/recovery и HAL restore PASS; ТЗ0.57.](F429_CMSIS_RTC_SLEEP.md)

[F429 ADC/DMA/units/failures:15/15 HW +3 повтора, HAL восстановлена; ТЗ0.56.](F429_CMSIS_ADC_DMA.md)

[F429 CMSIS baseline:7/7 HW, HAL восстановлена; ТЗ0.55. Пятый профиль в CI, ADC/RTC ещё впереди.](F429_CMSIS_BASELINE.md)

[F401 RTC/Sleep/deadline/recovery:20/20 HW +5 повторов, внешний timeout/recovery и HAL restore PASS; ТЗ0.54.](F401_CMSIS_RTC_SLEEP.md)

[F401 ADC/DMA/units/failures:15/15 HW и три положительных повтора, HAL восстановлен; ТЗ0.53.](F401_CMSIS_ADC_DMA.md)

[F401 CMSIS baseline: 7/7 HW через ST-Link/OpenOCD, HAL boot/blink восстановлены. Flash256/RAM64; ADC/RTC ещё не перенесены.](F401_CMSIS_BASELINE.md)

[Метрики аппаратных проверок и таблица результатов](HARDWARE_METRICS.md).

[Подготовка rc.2 и матрица приёмки](RC2_READINESS.md).

[Аппаратная приёмка HAL F030](F030_HAL_VALIDATION.md): 17/17, шесть повторов, timeout/recovery и восстановление исходной прошивки проверены на Windows/ST-Link/OpenOCD; ТЗ 0.40. API без изменений.

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

[Каталог техник TECH-001…008](TESTING_TECHNIQUES.md) — устойчивые ссылки из сценариев, условия сборки, ограничения и восстановление. При переносе HAL-сценариев сохранить ссылки TECH-001/003/004.

[Автономная HAL-регрессия F030](F030_HAL_REGRESSION.md): тестовый consumer, без изменения API.

- [F103 CMSIS: clocks/GPIO/SysTick/TIM2](F103_CMSIS_BASELINE.md).

- [F103 CMSIS: ADC/DMA/units/failures](F103_CMSIS_ADC_DMA.md).

- [F103 CMSIS: RTC/Sleep/deadlines/recovery](F103_CMSIS_RTC_SLEEP.md).

- [F411 CMSIS: clocks/GPIO/SysTick/TIM2](F411_CMSIS_BASELINE.md).

- [F411 CMSIS: ADC/DMA/units/failures](F411_CMSIS_ADC_DMA.md).

- [F411 CMSIS: RTC/Sleep/deadlines/recovery](F411_CMSIS_RTC_SLEEP.md).

[Итоговая сверка пяти профилей и оставшиеся HAL-проверки](CMSIS_ACCEPTANCE.md).

[HAL F030: пять GPIO/RCC-техник и варианты исходников](F030_HAL_GPIO_RCC.md).
