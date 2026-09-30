# F030: базовые CMSIS-проверки

[Документация](index.md) → F030 CMSIS · [English](../en/F030_CMSIS_BASELINE.md)

Протокол этапа: числа тестов и планы ниже относятся к указанной ревизии.
Текущий состав — [STATUS](STATUS.md), подготовка выпуска — [rc.2](RC2_READINESS.md).

30.09.2026, ветка `codex/f030-cmsis-baseline` от `4601888`.
NUCLEO-F030R8, штатный ST-Link/SWD 1 МГц, OpenOCD; runner Windows,
xPack GCC13.3.1-1.1, GDB14.2.90/Python3.11.4. UART не подключён.
CMSIS-only fixture: `tests/firmware`, без HAL и без тестовых hooks.

## Что изменилось

Только F030: HSI 8 МГц, AHB/APB /1, PA5 push-pull/low speed/no pull,
начальный Low. SysTick с LOAD=7999 формирует миллисекундный счётчик;
app_delay=500 задаёт интервал переключения LED. Ожидание использует WFI.
app_state.ticks по-прежнему считает итерации, а не миллисекунды.
F103/F411 сохраняют прежнее поведение.

Константный reload рассчитан на этапе компиляции: деление изменяемого
SystemCoreClock на Cortex-M0 потребовало бы __aeabi_uidiv из libgcc при
используемом -nostdlib. Профиль имеет фиксированную частоту, динамической
смены частоты здесь нет.

## Аппаратный результат

| Сценарий | Доказательство | Результат |
| :--- | :--- | :--- |
| HW_CI_BOOT | main, значения .data/.bss, достижение app_loop, рост счётчика | PASS |
| HW_CI_GPIO | PA5 clock/output, push-pull, speed, pull, initial Low | PASS |
| HW_CI_CLOCK | HSI ready/selected, делители, SystemCoreClock, SysTick LOAD/CTRL | PASS |
| HW_CI_BLINK | Low → High → Low; между остановками ≥500 firmware ms | PASS |

ELF SHA256: `05e6e50802131edb3cbfa1dd8e71db5830422a0bb35439031b732701b69668ea`.
Все четыре отчёта: `teardown=reset_run`. Локальные логи —
`build/f030-cmsis-baseline/`, JSON/JUnit — `tests/firmware/build/f030r8/hwtest/runs/`.
После опыта восстановлена прежняя HAL-прошивка BlackPill-проекта:
HW_BOOT PASS, reset_run. Стенд оставлен с HAL-приложением.

Повтор: configure/build preset f030r8, CTest f030r8-offline, затем штатный
`python -B -m stm32_gdbtest run --session tests/firmware/build/f030r8/hwtest/session.json
--test <ID> --stand <local.toml>` для каждого из четырёх ID. Локальный stand
выбирается явно. Старые десять шагов run_hw.py не включают новые CLOCK/BLINK;
их полный повтор и другие backend этим опытом не заявляются.

## Границы

Остановки меняют течение времени. Нет измерения точности HSI, потребления,
оптического мигания или частоты внешним прибором. Чтение SysTick CTRL очищает
COUNTFLAG; приложение использует IRQ-счётчик, а не флаг. WFI в приложении
сам по себе не доказывает прежние HW_SLEEP_* сценарии.
ADC/DMA/TIM3/RTC и HAL-specific отказы остаются в плане миграции.

Offline-регрессия: Windows host 96 тестов (8 skips); Linux Docker, архив Git index на case-sensitive filesystem — docs/host и девять пар F030/F103/F411 × GCC13/14/15: 13/13 PASS. Формат изменённых C-файлов и strict-проверка ТЗ пройдены.
