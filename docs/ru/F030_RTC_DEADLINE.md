# F030: дедлайн ожидания RTC

[Документация](index.md) · [English](../en/F030_RTC_DEADLINE.md)

Вторая ветка пакета: codex/f030-rtc-deadline от codex/f030-adc-busy (`3ba9c26`).
Firmware и API не менялись. HW_CI_RTC_DEADLINE останавливает rtc_wait при
error=3 и заменяет mask на0. Предикат готовности становится заведомо ложным,
при работающем SysTick требуется error3 через ≥1000 ticks, без продвижения
app_loop и публикации RTC events. BDCR не должен измениться.
Это проверка общего ожидания/распространения ошибки, не физический отказ LSI,
не тест всех стадий и не проверка несовместимого сохранённого RTC source.

Первый опыт дал ERROR после успешной проверки error3/дедлайна: RCC был недоступен
в контексте board_rtc_fault. Исправлено сохранением адреса &RCC->BDCR в rtc_wait
и чтением unsigned int по нему после отказа; адрес не захардкожен.
Контракт в RTC_IRQHandler не гарантирует доступность макроса в каждой точке
остановки, особенно внутри inline CMSIS-кода. Первоначальный отчёт сохранён.

На NUCLEO-F030R8/ST-Link/SWD1MHz/OpenOCD0.12.0, Windows/GCC13/GDB14.2.90:
исправленный HW PASS 20260930T173225. На том же ELF ADC_DMA и RTC_ALARM
после reset_run PASS 20260930T173248/20260930T173250. HAL восстановлен,
HW_BOOT PASS 20260930T173254, reset_run, MCU работает.
F030 build и CTest 19/19 PASS. Логи: build/f030-fault-batch/;
JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/.
Полный набор18 заново не запускался; предыдущие16 и ADC_BUSY имеют отдельные
доказательства на том же ELF из [RTC-протокола](F030_CMSIS_RTC.md).
