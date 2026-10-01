# F411 CMSIS: ADC/DMA, заводская калибровка и отказы

[Документация](index.md) · [English](../en/F411_CMSIS_ADC_DMA.md)

01.10.2026, рабочая копия codex/f411-cmsis-adc-dma от main cb17bdf.
WeAct BlackPill F411CE + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Без UART/внешней проводки.
Продолжение [baseline](F411_CMSIS_BASELINE.md); API/схемы и тег rc.2 неизменны.
SHA базы не обозначает SHA изменённой реализации.

## Реализация

ADC1 работает от PCLK2/2=8 МГц, scan CH18 (температура), затем CH17 (VREFINT),
по480 ADC cycles. TSVREFE включён, VBAT выключен, после ADON выдерживается2 мс.
Процедуры F1 RSTCAL/CAL нет. Источник конфигурации —
[RM0383](https://www.st.com/resource/en/reference_manual/dm00119316-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).

DMA2 Stream0/channel0, normal/direct mode, два halfword в SRAM, MINC,
TC/TE/DME interrupts, IRQ56/vector72. При NDTR=0 stream останавливается аппаратно.
ISR очищает flags через LIFCR W1C и публикует raw до увеличения sequence.
Каждый sample заново устанавливает NDTR, очищает ADC SR и переключает ADC DMA;
DDS сохраняет запросы между последовательностями, SWSTART запускает scan.
Инициализация ожидает выключения stream не более20 ticks; acquisition ждёт
уведомления20 ticks. Guard занятого stream — error6, ADON=0 — error3,
тайм-аут — error4, DMA error flags — error5, обнаруженный после завершения OVR — error7.

Заводские адреса по [DS10314](https://www.st.com/resource/en/datasheet/stm32f411ce.pdf):
VREFINT_CAL=0x1FFF7A2A, TS_CAL1=0x1FFF7A2C, TS_CAL2=0x1FFF7A2E;
условия3.3 В и30/110 °C. Адреса принадлежат F411 fixture, не общему ядру.
Чистая adc_convert_f411 принимает пять uint16 аргументов; int64 и libgcc
сохраняют точность промежуточного отношения raw/calibration. quality2 означает
FACTORY, не метрологическую точность. Окно VDDA2400–3600 мВ — ограничение приложения.
Равные/обратные точки, нулевые/насыщенные коды и неверный VDDA дают нулевой результат.

## Сценарии и результат

| HW_CI_* | Проверка |
| --- | --- |
| ADC_INIT | Clocks, ranks/sample times, stream config/addresses, NVIC/vector |
| ADC_DMA | Два естественных scan, exception72, TC без TE/DME/FE, публикация/останов stream |
| ADC_UNITS | Factory provenance, разумные VDDA/температура |
| ADC_VECTORS | Пять независимых точек:30/110/70/-10 °C и изменение VDDA |
| ADC_INVALID | 15 плохих raw/calibration аргументов +4 случая порядка точек/питания; нормальное восстановление |
| ADC_TIMEOUT | Маскирование IRQ56: NDTR0, но без публикации; error4 через ≥20 ticks |
| ADC_BUSY | EN перед sample: guard владения stream, error6 без публикации |
| ADC_DISABLED | ADON0: error3 без публикации |

**15/15 HW PASS**, включая семь baseline-сценариев. После каждой из трёх state-инъекций
ADC_DMA повторён: **3/3 PASS**. Исходная HAL восстановлена, HW_BOOT/HW_BLINK PASS,
reset_run, MCU работает. Пример результата:3300 мВ,28103 м°C,quality2.
Платы F030/F103 аппаратно не запускались.

ELF SHA256: `f590213d360c8952fef7e88aec2bc0b9fe547099c26483b1928690f8999e1853`.
Локальный протокол: build/f411-cmsis-adc-dma/f411-windows-full-20261001T113100Z/summary.json;
JSON/JUnit по ссылкам summary, исходники — tested-source-hashes.json. Артефакты gitignored.
Windows prepare/traceability:16/16 PASS.

## Ограничения и повтор

[TECH-001/002/006/007](TESTING_TECHNIQUES.md): CMSIS context в adc_f411.c,
MMIO-инъекции и подмена аргументов чистой арифметики. IRQ56 лежит в NVIC bank1.
DMA EN не аналог F0 ADSTART и не доказательство активной конверсии.
DMA errors, OVR и timeout выключения stream реализованы, но не инжектировались.
Нет метрологии, непрерывного потока/throughput, проверки внешних аналоговых входов
или HAL callbacks/return codes. GDB halt меняет время; тесты читают SRAM, не ADC_DR.

Сборка/prepare — presets f411ce/f411ce-offline в tests/firmware. Из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f411ce/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать F411/OpenOCD явно; после инъекций повторить ADC_DMA, в finally восстановить
HAL и проверить HW_BOOT/HW_BLINK. Следующая группа — RTC/Sleep/recovery.
GitHub Docs/Offline проверяются после push; gitlink потребителя пока не обновляется.

Локально Windows docs/host4/4 (98 unittest,8 платформенных skips), формат C/H PASS.
Linux Docker host и девять MCU/GCC сочетаний:10/10 PASS; логи в
build/f411-cmsis-adc-dma/linux-source/build/ci. Это offline, не Linux HW.
