# Перенос минимальных примеров на CMSIS

[Документация](index.md) → Миграция примеров · [English](../en/CMSIS_MIGRATION.md)

Решение владельца от 30.09.2026: минимальные примеры и актуальная матрица
регрессии развиваются в stm32-gdbtest. После CMSIS-миграции BlackPill-репозиторий
сохраняет самостоятельный F411-consumer на сопровождении по образцу BluePill.
Прошивки и специфичные сценарии остаются вне ядра модуля.

На `bc07625` уже есть CMSIS-only `tests/firmware` для F030/F103/F411 и
`examples/minimal-consumer` для F411. Используем их без создания дублей:
первый проект — регрессионная fixture, второй — пример подключения.
F401/F429 предстоит добавить; H503 остаётся на паузе. CMSIS относится к ARM,
для RISC-V нужны соответствующие startup/BSP.

## F030: сравнение с 17 HAL-сценариями

Первый этап выполнен: [boot/clock/GPIO/blink](F030_CMSIS_BASELINE.md) — 4/4
на Nucleo/ST-Link/OpenOCD. Таблица ниже сохраняет исходную инвентаризацию;
часть HW_CLOCK, относящаяся к периферии, ещё не перенесена.

Источник — профиль f030r8 BlackPill-проекта на `7a198d1`. Два имеющихся
CMSIS-сценария не заменяют все 17 исходных проверок.

| Исходные сценарии | CMSIS fixture / недостающая проверка |
| :--- | :--- |
| HW_BOOT | HW_CI_BOOT проверяет app_loop/ticks; отдельно сохранить main/fault |
| HW_GPIO | HW_CI_GPIO проверяет PA5 clock/output; добавить push-pull, pull, speed, initial level |
| HW_CLOCK | Нужны независимые ожидания частот/делителей и clocks периферии |
| HW_BLINK | Нужны High/Low и интервал ≥500 ms; app_state.ticks не миллисекунды |
| HW_ADC_DMA_INIT, HW_ADC_DMA_RUNTIME | ADC/DMA отсутствуют; нужны настройка, завершение, публикация |
| HW_TIM3_INIT, HW_TIM3_IRQ | TIM3/IRQ отсутствуют; нужны конфигурация и эффект обработчика |
| HW_RTC_INIT, HW_RTC_ALARM | RTC отсутствует; нужны настройка и повторное событие |
| HW_ADC_START_ERROR, HW_ADC_DMA_TIMEOUT | Определить отказ CMSIS-драйвера и дедлайн; HAL injection сохранить отдельной fixture |
| HW_ADC_UNITS, HW_ADC_INVALID, HW_ADC_VECTORS | Перенести арифметику, калибровку и независимые численные ожидания |
| HW_SLEEP_SYSTICK, HW_SLEEP_TIMER | Перенести WFI/wake sources и оговорки о влиянии отладчика |

Локально 30.09.2026: Windows, GCC13.3.1-1.1, preset f030r8 — build PASS,
`ctest --preset f030r8-offline` 3/3 (два prepare и traceability).
Runner не подключался к плате; прошивка стенда не менялась. Это не новый HW PASS.

## Порядок приёмки

1. Завершить F030 boot/clock/GPIO/blink, затем проверить на Nucleo со штатным
   ST-Link/SWD; перед HW назвать backend и процедуру восстановления HAL firmware.
2. Переносить timer/IRQ, ADC/DMA/арифметику, RTC, Sleep и отказы отдельными шагами.
   Для каждого сценария указать сохранённое, изменённое или потерянное доказательство.
3. Сверить F103/F411 и добавить F401/F429. HAL-specific API/macros оставить
   отдельной регрессией: CMSIS-код их не проверяет.
4. Опубликовать и принять примеры здесь до удаления активных копий из BlackPill.
   Исторические протоколы сохранить; новую матрицу вести здесь с SHA, ELF,
   MCU/backend/toolchain и ограничениями. Старый PASS не наследуется.
5. После переноса оптимизировать CI: измерить этапы, исключить повторные
   host-suite, рассмотреть кэш, сохраняя набор доказательств.

API/схемы/версия пока не меняются. Это план, не подтверждение новых MCU;
стенд К1921 не возобновляется. F411-приложение остаётся независимым consumer,
а небольшая F411 fixture модуля проверяет инфраструктуру.

Этап TIM3/IRQ выполнен: [6/6 HW PASS, mapping and limitations](F030_CMSIS_TIMER.md).

ADC/DMA F030: сырые отсчёты и timeout, API ядра без изменений. [ADC/DMA](F030_CMSIS_ADC_DMA.md).

F030: преобразование ADC и численные сценарии, API ядра без изменений. [ADC units](F030_CMSIS_ADC_UNITS.md).

F030 Sleep/WFI: профильные сценарии через GDB unwind, API ядра не меняется. [Sleep evidence](F030_CMSIS_SLEEP.md).
