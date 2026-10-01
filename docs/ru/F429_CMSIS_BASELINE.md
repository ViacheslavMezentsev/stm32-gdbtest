# F429 CMSIS: startup, clocks, GPIO, TIM2 и SysTick

[Документация](index.md) · [English](../en/F429_CMSIS_BASELINE.md)

01.10.2026, рабочая копия codex/f429-cmsis-baseline от main `9d22410`.
STM32F429I-DISCO (старая плата), STM32F429ZIT6, встроенный ST-Link/V2,
CN1/SWD, OpenOCD0.12.0, Windows, GCC13.3.1-1.1/GDB14.2.90.
Подключение подтверждено владельцем; UART и дополнительная проводка не нужны.

## Профиль и настройка

CMSIS STM32F429xx из CubeF4 V1.28.3. Flash 2 МиБ, обычная SRAM 192 КиБ;
CCM 64 КиБ в linker не включена. DMA в следующих группах должен использовать SRAM.
Ожидаемый DEV_ID 0x419; в этой серии прочитаны 0x419 и 2048 КиБ, identity.matches=true.
Исходные сведения сверены с действующим HAL-профилем F429 потребителя,
его linker, GPIO-конфигурацией и CMSIS stm32f429xx.h.

Минимальный пример использует HSI 16 МГц, AHB/APB1/APB2 /1, без PLL.
Это сознательная смена конфигурации относительно прежнего HAL-примера
(PLL 64 МГц, AHB/8, HCLK 8 МГц), а не подтверждение его PLL-настройки.
LD3/PG13 active-high, push-pull low-speed без pull, начальный Low.
SysTick LOAD 15999 даёт номинальный tick 1 мс; LED переключается каждые 500 ticks.
TIM2 PSC=15999/ARR=99: номинально 100 мс, IRQ28/vector44.
Startup копирует .data, очищает BSS; IRQ включается после очистки pending/UIF.

В board.c и startup.c добавлены отдельные ветки F429; ADC/RTC не вызываются
и не включены в эту сборку. API ядра, схемы и версия 0.1.0rc2 не меняются.

## Проверки и границы

| HW_CI_* | Доказательство |
| --- | --- |
| BOOT | .data/BSS при main, переход в app_loop и изменение счётчика |
| GPIO, BLINK | Регистры PG13, начальный Low и чередование через ≥500 firmware ticks |
| CLOCK | HSI/SYSCLK, делители, SystemCoreClock и SysTick |
| TIM2_INIT, TIM2_IRQ | PSC/ARR/NVIC/vector44, естественные IRQ, публикация и возврат в поток |
| SYSTICK_IRQ | vector15/exception15, счётчик ticks, возврат в поток |

[TECH-001/002/003](TESTING_TECHNIQUES.md): CMSIS-макросы в контексте board.c,
естественные IRQ, независимые ожидания. Для прежних HAL boot/GPIO/timer сохраняется
проверка конечного состояния и обработчика, но не handles/callbacks, аргументов HAL
или force_return. Проверки регистров не подтверждают излучение светодиода.
Точность HSI, jitter, потери IRQ и изолированный WFI не измерялись.

## Результат и повтор

Windows build, prepare/traceability **8/8 PASS**. Аппаратный набор **7/7 PASS**,
image_verified и reset_run во всех отчётах. После серии исходная HAL-прошивка
восстановлена, HW_BOOT/HW_BLINK PASS; MCU оставлен running.
ELF SHA256: `237d2926b19f8c745c4745b7a1ef2a5fe0e60d58ab6316d23d1c0b8676ac8024`.
Артефакты build/f429-cmsis-baseline: f429-windows-full-20261001T140318Z/summary.json
и tested-source-hashes.json. SHA базы не обозначает изменённые исходники.
Личные пути/serial, ELF и JSON/JUnit не коммитятся.

Presets f429zi/f429zi-offline в tests/firmware. Из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f429zi/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать stand DISCO/OpenOCD явно; в finally восстановить исходную HAL и проверить boot/blink.
Аппаратный helper run_hw.py сохраняет прежнюю матрицу трёх плат; новые семь
сценариев запускаются штатным CLI. CI build/prepare добавляет пятый профиль на GCC13/14/15.

Короткая серия прошла без USB-сбоев; это не отменяет исторического ограничения
ST-Link/V2 при последовательных запусках. На первом сбое серия останавливается;
переподключение USB согласуется с владельцем. Firmware отладчика не менялась.
ADC/DMA/units/failures и RTC/Sleep/deadline/recovery — следующие группы.
Новые backend, Linux HW, timeout/recovery и full-image HW здесь не проверялись.
GitHub Docs/полный Offline опубликованного SHA проверяются отдельно до land.

Локальная регрессия: Windows docs/host4/4 (98 unittest, 8 платформенных skips); Linux Docker format/host и 15 сочетаний MCU/GCC — 17/17 PASS. Логи: build/f429-cmsis-baseline/linux-source/build/ci; Windows — windows-docs-host.json и windows-host.log рядом. Исторический CMSIS-срез обновлён до 5 моделей плат / 85 сценариев; повторы в сумму не входят.
