# F030: итоговая сверка HAL → CMSIS

[Документация](index.md) · [English](../en/F030_CMSIS_ACCEPTANCE.md)

Третья ветка пакета — codex/f030-cmsis-acceptance от codex/f030-rtc-deadline
(`769226b`). Сверены 17 HAL-сценариев профиля f030r8 потребителя на `50adc35`
и 18 CMSIS-сценариев tests/firmware. Число сценариев не является покрытием кода.

## Соответствие доказательств

| HAL-сценарий | CMSIS-сценарий (префикс HW_CI_) | Сохранено / изменено / не перенесено |
| --- | --- | --- |
| HW_BOOT | BOOT | main и app_loop, BSS/инициализированные данные; fault trap сохранён, отдельная инъекция HardFault не выполнялась |
| HW_CLOCK | CLOCK, ADC_INIT, TIM3_INIT | HSI8/AHB/APB /1 и clocks ADC/DMA/TIM3; распределено по сценариям, без HAL RCC predicates |
| HW_GPIO | GPIO | PA5, режим, тип, скорость, pull и начальный Low сохранены |
| HW_BLINK | BLINK | High/Low, ≥500 ticks SysTick; нет утверждения о точности физического периода |
| HW_ADC_DMA_INIT | ADC_INIT | Регистры ADC/DMA, scan16/17, sample time, normal halfwords; поля HAL handles не проверяются |
| HW_ADC_DMA_RUNTIME | ADC_DMA | Два завершения, сырые данные и публикация; вместо HAL callback — DMA IRQ, проверка handle потеряна |
| HW_TIM3_INIT | TIM3_INIT | PSC7999/ARR99; CMSIS проверяет уже запущенный таймер, промежуточное CEN=0 HAL не перенесено |
| HW_TIM3_IRQ | TIM3_IRQ | Естественный IRQ, UIF, счётчик, возврат thread mode; HAL callback handle отсутствует |
| HW_RTC_INIT | RTC_INIT | LSI,127/311, clock enable, output off; добавлены EXTI/NVIC/вектор/маски |
| HW_RTC_ALARM | RTC_ALARM | Два естественных Alarm A, публикация; нет HAL callback/handle |
| HW_ADC_START_ERROR | ADC_BUSY | Замена: реальный занятой ADC → error6. force_return HAL_ERROR и путь HAL не перенесены |
| HW_ADC_DMA_TIMEOUT | ADC_TIMEOUT | Нет публикации → deadline; вместо подавления HAL callback отключается DMA IRQ |
| HW_ADC_UNITS | ADC_UNITS | Калибровка F030, quality3 и sanity; не измерение точности датчика |
| HW_ADC_INVALID | ADC_INVALID | Невалидный вход → нулевые поля, затем восстановление; расширено до четырёх входов и границ |
| HW_ADC_VECTORS | ADC_VECTORS | Аналитическая опора и дополнительные векторы; фиксированные ожидания, C integer truncation |
| HW_SLEEP_SYSTICK | SLEEP_SYSTICK | IRQ и продвижение после обычного Sleep; добавлен interrupted WFI context; вызов HAL не проверяется |
| HW_SLEEP_TIMER | SLEEP_TIM3 | Изоляция TIM3 от SysTick, контекст WFI и дальнейшее выполнение; не измерение тока |

RTC_DEADLINE — дополнительная проверка общего ожидания с инъекцией mask=0,
не эквивалент физической неисправности LSI или проверки всех RTC ошибок.

## Проверенный объём

Один ELF SHA256 `b911213338acc2de1b0d47a41d7c0b23a50974ba8f78370e041f2afbc2a00e9e`:
16/16 в [RTC-этапе](F030_CMSIS_RTC.md), затем [ADC_BUSY](F030_ADC_BUSY.md) и
[RTC_DEADLINE](F030_RTC_DEADLINE.md) отдельно; это не единый прогон18/18.
После инъекций нормальные ADC_DMA и RTC_ALARM прошли повторно.
NUCLEO-F030R8/ST-Link/SWD/OpenOCD, Windows/GCC13; HAL восстановлен и running.
GCC14/15 — только build/prepare. Иные backend/ОС аппаратно в этом пакете не проверены.

## Решение и оставшиеся шаги

Функциональный CMSIS baseline F030 подтверждён в указанном объёме. Удалять HAL
профиль потребителя ещё нельзя: он сохраняет регрессию HAL contracts/macros,
callback handles и force_return. До удаления нужен отдельный минимальный HAL
fixture в модуле с теми же доказательствами; старые результаты не заменяют новый запуск.

Дальнейшие отказы ADC (DMA TE, clock/calibration/ready) и RTC (source mismatch,
остальные стадии) остаются открытыми. Backup retention, rollover, точность,
Stop/Standby и потребление — отдельные задачи, не критерии текущего baseline.
Дальше можно готовить CMSIS F103/F411 без удаления F030 HAL и без объявления
полной миграции всех профилей. Смену стенда согласовать с владельцем отдельно.

## Пакет веток

1. codex/f030-adc-busy, `3ba9c26`, база `5d09823`.
2. codex/f030-rtc-deadline, `769226b`, база первой ветки.
3. codex/f030-cmsis-acceptance, база второй ветки; только документация.

Владелец публикует все три ветки. Для каждого SHA должны завершиться Docs и
все jobs Offline. Land выполняется последовательно, fast-forward, без squash
и изменения уже проверенных коммитов. После любого rebase CI нового SHA
проверяется заново. Push не означает разрешения на land. После принятия пакета
потребитель обновляет gitlink один раз отдельной веткой со своим CI.

## Локальные проверки пакета

Каждый из трёх снимков отдельно прошёл Linux Docker docs/host и девять
firmware-пар F030/F103/F411 × GCC13/14/15: 13/13 этапов на каждой ветке.
Отчёты: build/f030-fault-batch/b1, b2, b3/linux-ci/summary.json.
Windows host: 96 тестов, 8 skips; F030 CTest: 18/18 на первой ветке,
19/19 на второй (третья меняет только документацию). Исходный RTC ERROR:
20260930T173151.880173Z-HW_CI_RTC_DEADLINE-35952; исправленный PASS и восстановление
приведены в протоколе. GitHub CI каждого опубликованного SHA ещё предстоит проверить.

Актуализация после публикации: пакет вместе с четвёртой веткой переименования
принят в main `cea01f9`; Docs и все пять jobs Offline каждого SHA SUCCESS.
Потребитель обновлён и принят на `0c8c966` после CI пяти профилей. Следующий
этап — [отдельная HAL-регрессия](F030_HAL_REGRESSION.md).
