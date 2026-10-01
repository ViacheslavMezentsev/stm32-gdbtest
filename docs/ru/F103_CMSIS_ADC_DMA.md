# F103 CMSIS: ADC, DMA, физические единицы и отказы

[Документация](index.md) · [English](../en/F103_CMSIS_ADC_DMA.md)

01.10.2026, codex/f103-cmsis-adc-dma от main 352417c. Проверена рабочая копия,
SHA базы не объявляется SHA изменённого кода. WeAct BluePill-Plus F103C8,
J-Link 8.32/SWD, Windows, GCC 13.3.1-1.1/GDB 14.2.90. Без UART/внешних соединений.
Группа продолжает [clocks/GPIO/SysTick/TIM2](F103_CMSIS_BASELINE.md).

## Реализация

ADC1 получает PCLK2/2 = 4 МГц; после включения выдерживается 2 мс,
выполняются RSTCAL и CAL с отдельными дедлайнами 20 мс. Регулярный scan:
CH16 (температура), затем CH17 (VREFINT), по 239.5 cycles. TSVREFE получает
2 мс на установление. EXTSEL=7/EXTTRIG/SWSTART запускают одну последовательность.
DMA1 channel1 работает в normal mode: два halfword в SRAM, IRQ 11/vector 27.
DMA включается после калибровки; ISR публикует raw до увеличения счётчика.
Повторный sample заново устанавливает CNDTR, обработчик выключает DMA и очищает флаги.

Источник конфигурации: [RM0008](https://www.st.com/resource/en/reference_manual/rm0008-stm32f103xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).
Для расчётов [DS5319](https://www.st.com/resource/en/datasheet/stm32f103c8.pdf)
задаёт типовые VREFINT=1.20 В, V25=1.43 В, slope=4.3 мВ/°C.
Используется отношение сырых кодов, int64 и libgcc; окно приложения 2400–3600 мВ.
`quality=1` означает TYPICAL, не заводскую калибровку или точность 0.001 °C.
Чтения калибровочных адресов F030/F411 нет. Формула и четыре аналитических
вектора сохранены по прежнему adc_convert_typical потребителя; ядро модуля не меняется.

## Проверки

| Новые сценарии | Доказательство |
| --- | --- |
| ADC_INIT | Clocks, CR1/CR2, ranks/sample time, DMA buffer/configuration, NVIC/vector |
| ADC_DMA | Две естественные последовательности, exception 27/TC без TE, публикация и останов DMA |
| ADC_UNITS | TYPICAL и разумный диапазон реального результата |
| ADC_VECTORS | Четыре фиксированных вектора: 25, -25, 100 °C и изменение VDDA |
| ADC_INVALID | Восемь невалидных наборов, затем нормальное измерение |
| ADC_TIMEOUT | ICER IRQ 11: DMA завершён, уведомления нет, error 4 через ≥20 ticks |
| ADC_BUSY | DMA EN до sample: error 6 без публикации; это guard владения каналом |
| ADC_DISABLED | ADON=0 до sample: error 3 без публикации |

Полные ID имеют префикс HW_CI_. TECH-001/002 применены к CMSIS-контексту,
[TECH-006/007](TESTING_TECHNIQUES.md) — к MMIO и аргументам арифметики.
Контракты проверяют macro context adc_f103.c и сигнатуру adc_convert_f103.

**15/15 HW PASS**, включая семь прежних сценариев; после каждого из трёх
аппаратных state-инъекций ADC_DMA отдельно повторён: ещё **3/3 PASS**.
Исходная HAL-прошивка потребителя восстановлена, HW_BOOT/HW_BLINK PASS,
reset_run; плата оставлена работающей. Пример чтения: 3313 мВ, 28809 м°C,
quality 1; это не независимая метрологическая проверка.

ELF SHA256: `39cbb960bb62fcb65b1bf9c962b272997270de2abc63ca16723774f525a12b20`.
Локальный протокол: build/f103-cmsis-adc-dma/
f103-windows-full-20261001T082723Z/summary.json; JSON/JUnit —
tests/firmware/build/f103c8/hwtest/runs. Summary содержит ссылки на каждый результат.

## Ограничения и повтор

В F1 нет F0 ADSTART: DMA EN не доказывает текущую конверсию ADC. Сценарий
ADC_BUSY проверяет только оговорённый guard, а IRQ masking не моделирует
обрыв аналогового входа. TE/error 5 и дедлайны RSTCAL/CAL реализованы, но в этой
группе не инжектировались. Нет доказательства точности датчика, DMA throughput,
отсутствия потерь при непрерывном потоке или HAL handles/callbacks/return codes.
F103 не предоставляет F0 OVR: соответствующее доказательство не переносится.
GDB halt меняет время; чтение ADC_DR имеет побочные эффекты, сценарии используют SRAM.
RTC/Sleep — следующая группа, lifecycle pack/full-image здесь не повторялся.

Сборка/prepare: presets f103c8 и f103c8-offline из tests/firmware.
Аппаратный запуск каждого ID из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f103c8/hwtest/session.json --test <ID> --stand <local.toml>`.
Stand — BluePill/J-Link; перед серией проверить restore-session потребителя,
после отказных сценариев повторить ADC_DMA, в finally восстановить HAL и boot/blink.

Локальная регрессия: Windows docs/host 4/4, F103 CTest 16/16; Linux Docker
host и девять сочетаний F030/F103/F411 × GCC13/14/15 — 10/10 этапов PASS.
Включены prepare, отрицательные contracts и image policy. Логи:
build/f103-cmsis-adc-dma/linux-source/build/ci. Формат C — PASS.
GitHub CI проверяется отдельно после push; другие платы аппаратно не запускались.
