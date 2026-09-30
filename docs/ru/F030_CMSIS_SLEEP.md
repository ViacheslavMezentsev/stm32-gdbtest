# F030 CMSIS: Sleep/WFI и источники IRQ

[Документация](index.md) · [English](../en/F030_CMSIS_SLEEP.md)

30.09.2026, codex/f030-cmsis-sleep от a84b742. NUCLEO-F030R8,
штатный ST-Link V2J45M31/SWD 1 МГц, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90/Python3.11.4; без UART/внешних соединений.
Firmware и ядро не менялись; добавлены сценарии и CI prepare.

## Метод

Сценарии входят в board_delay_ms при delay_ms=500, после ADC-публикации.
SCR SLEEPDEEP/SLEEPONEXIT должны быть сброшены. Через журналируемые изменения
NVIC/SysTick поочерёдно оставляются SysTick либо TIM3. Для TIM3 SysTick
останавливается, pending SysTick снимается через ICSR.PENDSTCLR.

В обработчике проверяется IPSR (15/32), затем GDB восстанавливает прерванный
кадр: Frame.older/type/pc/name, с пропуском signal trampoline. Требуется
board_delay_ms и 16-битная инструкция 0xBF30 (WFI) непосредственно перед PC.
IRQ может прийти до WFI; допускается максимум восемь попыток с сохранением
всех контекстов. Нет контекста WFI — FAIL, невозможность unwind — ERROR,
никакого перехода к более слабому PASS. Это профильный Cortex-M тест,
не универсальная функция ядра для других архитектур.

Настройки восстанавливаются в finally; штатный teardown также reset_run.
После восстановления — возврат в app_loop, продвижение счётчиков и сохранённый
ADC sequence 1. Для TIM3 при выключенном SysTick его счётчик не меняется.
Чтение SysTick CTRL очищает COUNTFLAG, который приложение не использует.

## Доказательство

**2/2 новых HW PASS**, 20260930T163701/20260930T163704. SysTick с первой
попытки: interrupted PC=0x080001BC, предыдущая инструкция WFI.
TIM3: первая остановка до WFI (PC=0x080001B4, halfword 0x2000), вторая —
после WFI (PC=0x080001BC). Одна лишь остановка в обработчике была бы слабее.
ELF SHA256 совпадает с этапом ADC units:
`cd52b5cbac535952fb4069b067c9e24bf536172126c0a98bdd40548a89e3e01b`.
Прежние 12 сценариев в этом опыте заново не запускались; это не единая
серия 14/14. [Их протокол](F030_CMSIS_ADC_UNITS.md) относится к тому же ELF.
JSON/JUnit — tests/firmware/build/f030r8/hwtest/runs/;
логи — build/f030-cmsis-sleep/. HAL восстановлен, HW_BOOT PASS
20260930T163707, reset_run; MCU оставлен работающим.

## Границы

Сохраняется смысл HW_SLEEP_SYSTICK/TIMER: обычный Sleep-путь и дальнейшее
выполнение, добавляется анализ прерванного PC. Нет наблюдения DHCSR.S_SLEEP,
измерения residency, тока или времени пробуждения. WFI мог завершиться быстро
из-за pending IRQ; отладчик меняет исполнение. Это не Stop/Standby.
GCC14/15 проверяются build/prepare; unwind на них аппаратно ещё не проверен.
HAL_PWR_EnterSLEEPMode не вызывается и не проверяется. Далее RTC и отдельная
приёмка оставшихся HAL-specific/отказных сценариев перед завершением миграции.

Локально: F030 CTest 15/15; Windows host 96 (8 skips); Linux Docker docs/host и F030/F103/F411 × GCC13/14/15 — 13/13 этапов PASS. Архив Git index извлечён на case-sensitive filesystem; strict ТЗ PASS.
