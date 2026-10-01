# HAL F030: GPIO/RCC и варианты исходников

[Документация](index.md) · [English](../en/F030_HAL_GPIO_RCC.md)

Ветка `codex/f030-hal-gpio-rcc` зависит от аудита `4c51122`.
Расширяет исходные 17 cases в tests/hal-f030 до 22; firmware не меняется.
Пять техник перенесены по смыслу из потребителя84a257e, не как доказательство
совместимости HAL F1/F4. См. [сверку](CMSIS_ACCEPTANCE.md).

## Новые проверки

| ID | Проверка |
| --- | --- |
| HW_GPIO_ARGUMENTS | HAL_GPIO_Init(GPIOA), Pin PA5, output push-pull, no pull, low speed; затем MODER |
| HW_GPIO_FILTERED_CALL | Условный останов на PA5 High перед TogglePin, затем Low после вызова |
| HW_RCC_ERROR | force_return HAL_ERROR из OscConfig → Error_Handler |
| HW_RCC_OSC_NULL | NULL аргумент OscConfig → штатный HAL_ERROR → Error_Handler |
| HW_RCC_CLOCK_NULL | NULL аргумент ClockConfig → штатный HAL_ERROR → Error_Handler |

NULL проверяется HAL до assert и разыменования. Это ошибки аргументов и синтетический
код возврата, не физические отказы генератора. Сценарии используют строгие контракты
типов, enum и source-review hash. [TECH-009](TESTING_TECHNIQUES.md#tech-009) описывает
контекст аргументов и выбор варианта; TECH-004 сохраняет force_return.

## Различие HAL Windows и CI

Одинаковое имя каталога CubeF0 V1.11.6 не гарантирует одинаковые исходники.
Установленная Windows-копия RCC имеет mutable pointers; закреплённая CI-копия
(HAL1.7.8) — const pointers. В обоих файлах NULL возвращает HAL_ERROR до assert/dereference.
Первые Linux prepare правильно завершились ERROR: тип OscConfig не совпал,
а source-review для двух NULL-cases отверг другой хеш. Проверки не ослаблены.

configure_profile.py выбирает только два вручную проверенных SHA256 RCC:

| SHA256 stm32f0xx_hal_rcc.c | RCC аргументы |
| --- | --- |
| fe601fa20f95e48d4bb2a9dd7409ff4d0637e184d6b3c4be4207777b246b2856 | mutable |
| 7ddf83d26b8b9b268df2d1b3c000835360b555aa09727a4c5471e67220d43187 | const |

Выбор зависит от содержимого файла, не ОС. CMake создаёт профиль в build/profile;
runner проверяет выбранный hash по manifest и типы по ELF. Неизвестный файл
останавливает configure до сервера. Не добавлять его hash без анализа сигнатур
и NULL guards. Исходные хеши миграции сохранены в provenance вместе с описанием расширения.
API/схема ядра не изменены; это механизм fixture. CMake отслеживает профиль,
селектор и RCC-файл для повторной конфигурации.

## Проверки и ограничения

Windows GCC13: 24/24 offline (22 prepare, traceability, inventory/imports/provenance).
Linux Docker: host PASS; HAL — 24 CTest, 22 prepare и пять отрицательных контрактов PASS.
Селектор отдельно проверен для двух типов и отклонения неизвестного hash.
Windows host также PASS. Linux HW, GCC14/15 HAL и Release/LTO здесь не проверялись.

Первый HW-набор прошёл 22 cases, 15 ADC/TIM3/RTC повторов после пяти инъекций,
ожидаемый timeout ERROR с маркером входа и reset_run host recovery, затем ADC PASS.
Автоматический restore остановился до сервера из-за WinError5 записи каталога отчёта.
Исходный ERROR сохранён: tests/hal-f030/build/validation/20261001T154906.539459Z.
Отдельное восстановление с разрешённым доступом: HW_BOOT/HW_BLINK PASS
(20261001T155154.356160Z и 20261001T155157.103743Z).
Окончательная серия после выбора вариантов описана ниже.

Повтор: команды build/prepare из [README fixture](../../tests/hal-f030/README.md),
затем run_hw.py с явными --stand и --restore-session. NUCLEO-F030R8,
родной ST-Link/OpenOCD/SWD, Windows. Не запускать без подтверждения стенда.
Серия останавливается при ошибке и пытается восстановить исходную прошивку.

Исторические 98 CMSIS cases в README не увеличиваются от этих HAL cases.
После CI и land этой группы можно переходить к F411-consumer; удаление старых
профилей остаётся отдельным шагом после его проверки. H503/К1921 не затронуты.

## Итоговая серия

tests/hal-f030/build/validation/20261001T155503.591790Z/summary.json:
22/22 HW, 15/15 повторов, ожидаемый timeout ERROR/recovery, ADC после recovery PASS,
автоматический restore HW_BOOT/HW_BLINK PASS; restored=true, MCU running.
ELF SHA256: `f2a2a2a98d8b95d080a78071543f7fd7d2a1f828dfaf3764c1ae53da39202fed`.
Всего 41 этап, включая один ожидаемый ERROR; это не «41/41 PASS».
Исходные ошибки сохранены; USB-сбоев в этой серии не было.
