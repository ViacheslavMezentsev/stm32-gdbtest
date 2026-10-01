# Итоговая сверка HAL → CMSIS для пяти профилей

[Документация](index.md) · [English](../en/CMSIS_ACCEPTANCE.md)

Срез 01.10.2026: модуль `b8d66e0`, потребитель
[stm32-hwtest-blackpill на 84a257e](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/tree/84a257e8825eeebaca3aed80e29cfe5f34235f53).
Сверены декораторы `@case` в `profiles/*/tests/board`, общие реализации
`tests/scenarios` потребителя и `tests/firmware/profiles/*/tests/board` модуля.
Экспериментальные negative API cases, host-тесты, prepare и повторы в числа не включены.
Это анализ исходников и уже сохранённых протоколов, без нового аппаратного запуска.

## Состав и доказательства

| Профиль | HAL board cases | CMSIS board cases | Аппаратное доказательство CMSIS |
| --- | ---: | ---: | --- |
| f030r8 | 17 | 18 | [Приёмка F030](F030_CMSIS_ACCEPTANCE.md): 16 + 1 + 1 на одном ELF, не единая серия 18/18 |
| f103c8 | 22 | 20 | [F103 RTC/Sleep](F103_CMSIS_RTC_SLEEP.md), J-Link/SWD |
| f401cc | 22 | 20 | [F401 RTC/Sleep](F401_CMSIS_RTC_SLEEP.md), ST-Link/OpenOCD/SWD |
| f411ce | 22 | 20 | [F411 RTC/Sleep](F411_CMSIS_RTC_SLEEP.md), ST-Link/OpenOCD/SWD |
| f429zi | 22 | 20 | [F429 RTC/Sleep](F429_CMSIS_RTC_SLEEP.md), ST-Link/V2/OpenOCD/SWD |
| Итого | 105 | 98 | Разные ревизии и ELF; не единая кампания текущего SHA |

Меньшее число CMSIS cases не означает потерю семи одинаковых проверок: сценарии
перегруппированы, HAL API заменён регистрами, добавлены новые отказы.
Числа не являются покрытием кода. Версии, ELF и пределы доказательств — в
[метриках](HARDWARE_METRICS.md) и профильных протоколах. Windows HW не подтверждает
Linux HW; сборки GCC14/15 не подтверждают аппаратный запуск на этих компиляторах.

## Соответствие групп

Ниже CMSIS ID приведены без префикса `HW_CI_`; HAL ID — без `HW_`.
Для F030 используется TIM3, для остальных TIM2.

| HAL | CMSIS | Что сохраняется и что меняется |
| --- | --- | --- |
| BOOT | BOOT | Startup, данные и достижение приложения; это не полный тест fault paths |
| CLOCK | CLOCK, ADC_INIT, TIMx_INIT | Настройка clocks; CMSIS masks вместо HAL predicates, не идентичная HAL-конфигурация PLL |
| GPIO, BLINK | GPIO, BLINK | Профильные pin/level, конфигурация и переключение; ticks не доказывают физическую точность периода |
| TIMx_INIT, TIMx_IRQ | TIMx_INIT, TIMx_IRQ | Настройка и естественный IRQ; HAL handle/callback и промежуточное состояние до start отсутствуют |
| ADC_DMA_INIT, ADC_DMA_RUNTIME | ADC_INIT, ADC_DMA | Scan/DMA, сырые данные и публикация; IRQ вместо HAL callback/handle |
| ADC_UNITS, ADC_VECTORS, ADC_INVALID | ADC_UNITS, ADC_VECTORS, ADC_INVALID | Арифметика, независимые векторы, невалидный вход; профильная калибровка не метрологическая проверка |
| ADC_START_ERROR | ADC_BUSY | Изменённое доказательство: занятый ADC вместо подмены возврата HAL_ERROR; прежний путь сохраняет HAL fixture |
| ADC_DMA_TIMEOUT | ADC_TIMEOUT | Дедлайн без публикации; отключение IRQ вместо подавления HAL callback |
| RTC_INIT, RTC_ALARM | RTC_INIT, RTC_ALARM | LSI/Alarm/публикация; F103 counter RTC отличается от календарного RTC F0/F4; HAL callbacks не проверяются |
| SLEEP_SYSTICK, SLEEP_TIMER | SLEEP_SYSTICK, SLEEP_TIMx | WFI, изоляция источника IRQ и возврат; без HAL API, Stop/Standby и измерения тока |
| Нет прямого аналога | RTC_DEADLINE | Инъекция mask аргумента ожидания; не физический отказ LSI и не проверка всех wait states |
| Нет отдельного case в HAL | SYSTICK_IRQ, ADC_DISABLED | Дополнительные cases F103/F401/F411/F429; у F030 отдельных cases нет |

Подробная таблица F030 остаётся в [его приёмке](F030_CMSIS_ACCEPTANCE.md).
В [каталоге техник](TESTING_TECHNIQUES.md) сохраняются TECH-001…008: контекст
макросов, IRQ/callback, инъекции, численные векторы и interrupted WFI.

## Что ещё нельзя удалить

[HAL fixture F030](F030_HAL_VALIDATION.md) имеет аппаратное подтверждение 17/17,
сохраняет handles, callbacks, макросы и `force_return` для ADC. Это не регрессия
всех HAL F1/F4 API. В четырёх HAL-профилях остаются пять дополнительных cases:

| ID | Доказательство, которое CMSIS/F030 fixture не заменяет |
| --- | --- |
| HW_GPIO_ARGUMENTS | Поля GPIO_Init в HAL_GPIO_Init и применение конфигурации |
| HW_GPIO_FILTERED_CALL | Условный останов на конкретном HAL_GPIO_TogglePin и изменение ODR |
| HW_RCC_ERROR | force_return HAL_ERROR из HAL_RCC_OscConfig → Error_Handler |
| HW_RCC_OSC_NULL | Подмена указателя RCC_OscInitStruct на NULL → Error_Handler |
| HW_RCC_CLOCK_NULL | Подмена указателя RCC_ClkInitStruct на NULL → Error_Handler |

Перед удалением исходников сохранить эти техники одной группой в самостоятельной
HAL-регрессии модуля: использовать существующий F030 fixture, если его HAL позволяет
сохранить смысл проверок; иначе отдельный минимальный F4 fixture. До выбора сверить
исходники HAL, DWARF scope, наличие функций и source-review contracts. Перенос на
другое семейство сохраняет технику, но не доказывает поведение HAL остальных MCU.
Нужны build/prepare, аппаратный запуск, положительные повторы после инъекций,
recovery/restore и ссылки на техники. До этого старые профили остаются доступны.

## Порядок завершения

1. Принять RTC/Sleep `b8d66e0`, затем эту документальную ветку
   `codex/cmsis-migration-audit`; она зависит от RTC/Sleep. Для обеих — Docs и полный Offline.
2. Сохранить пять дополнительных HAL-проверок одним пакетом. Стенд выбрать
   после анализа HAL; на этом этапе переподключать платы не требуется.
3. Перевести независимый BlackPill F411-consumer на CMSIS, обновить gitlink после
   принятия модуля; проверить build/prepare, HW и recovery на F411CE/ST-Link.
4. Только затем сократить потребителя до F411, сохранив историю и ссылки на
   перенесённые примеры, лицензии, методику и протоколы. H503 остаётся на паузе;
   К1921 и errata-материалы не удалять как якобы эквивалентные STM32 fixtures.
5. Оптимизировать CI после переноса. Автоматическая полная HW-кампания и её
   метрики остаются отдельным этапом; 98 исторических cases не заменяют такую кампанию.

Вывод: периферийный CMSIS baseline пяти профилей имеет аппаратные доказательства;
полное разделение репозиториев ещё не закончено. Ядро, API, схемы и требования ТЗ
этой сверкой не изменяются.

[HAL F030: пять GPIO/RCC-техник и варианты исходников](F030_HAL_GPIO_RCC.md).
