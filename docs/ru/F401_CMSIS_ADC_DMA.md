# F401 CMSIS: ADC, DMA, арифметика и отказы

[Документация](index.md) · [English](../en/F401_CMSIS_ADC_DMA.md)

01.10.2026, рабочая копия codex/f401-cmsis-adc-dma от main `ed5557f`.
WeAct BlackPill F401CC + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Продолжение [baseline](F401_CMSIS_BASELINE.md).

## Настройка и источники ожиданий

ADC1 scan CH16 температуры и CH17 VREFINT — не CH18 F411. PCLK2/2=8 МГц,
480 cycles (60 мкс), TSVREFE без VBAT, ADON/DMA/DDS; после power-up задержка2 мс.
DMA2 stream0/channel0: два halfword в SRAM, normal/direct, IRQ56/vector72.
TC публикует raw до счётчика завершений; stream flags очищаются записью LIFCR.
Новый набор не использует F1-процедуру калибровки ADC.

[DS9716, таблицы73/76](https://www.st.com/resource/en/datasheet/stm32f401vc.pdf)
подтверждает заводские TS_CAL1/2 (30/110°C) и VREFINT_CAL при3.3 В по адресам
0x1FFF7A2C/2E/2A. Каналы и IRQ сверены с CubeF4 V1.28.3 CMSIS/HAL headers
и прежним HAL-профилем потребителя. Модуль firmware использует только CMSIS.

Чистая арифметика F401/F411 общая: `adc_convert_f411` переименована в
`adc_convert_f4_factory`, формула и ограничения не изменены; контракты и сценарии
F411 обновлены. Это символ fixture, не изменение API stm32-gdbtest.
Quality2 означает происхождение калибровки, не заявленную точность температуры.

## Сценарии

| HW_CI_* | Доказательство |
| --- | --- |
| ADC_INIT, ADC_DMA | Регистры, SRAM, NVIC/vector; две естественные последовательности и публикация raw |
| ADC_UNITS | Заводское происхождение, правдоподобные VDDA/температура |
| ADC_VECTORS | Пять независимых аналитических точек: anchors, midpoint, отрицательная температура, компенсация VDDA |
| ADC_INVALID | 19 входов: нули/насыщение/uint16 max, равные/обратные калибровки, VDDA вне окна; затем нормальное чтение |
| ADC_TIMEOUT | Маска IRQ56: DMA заканчивается без уведомления, error4 через ≥20 ticks |
| ADC_BUSY | EN stream до запуска: guard владения DMA, error6, не признак активного ADC |
| ADC_DISABLED | Снятие ADON: error3, без публикации, не подмена HAL return code |

[TECH-001/002/006/007](TESTING_TECHNIQUES.md): macro context, естественные IRQ,
инъекция состояния, арифметические векторы. Исходные HAL init/runtime/units/timeout
заменены CMSIS-проверками; handles/callbacks/HAL return paths не проверяются.
Физические DMA errors, OVR и stream-disable timeout реализованы, но не инжектировались.

## Результаты и повтор

**15/15 HW PASS**, после timeout/busy/disabled ещё **3/3 ADC_DMA PASS**.
Исходная HAL F401 восстановлена, HW_BOOT/HW_BLINK PASS, MCU оставлен running.
Один пример измерения: VDDA3286 мВ, температура29770 м°C, quality2; это не метрология.
Windows build и prepare/traceability16/16 PASS. Другие платы не запускались;
F411 после переименования converter проверяется только offline.

ELF SHA256: `35bde810d6ade0774dd4c16b952bff98bb312cb309d6af955daeae2d45cbf11f`.
Артефакты build/f401-cmsis-adc-dma: f401-windows-full-20261001T132205Z/summary.json
и tested-source-hashes.json. SHA базы не обозначает изменённые исходники.
Presets f401cc/f401cc-offline из tests/firmware; CLI run с явным stand.
Внешний host timeout/recovery и full-image HW в этой группе не повторялись.
Следующая группа — RTC/Sleep/deadline/recovery; API/схемы/тег rc.2 неизменны.

Локальная регрессия: Windows docs/host4/4 (98 unittest,8 платформенных skips), Linux Docker format/host и12 MCU/GCC сочетаний14/14 PASS. Логи — build/f401-cmsis-adc-dma/linux-source/build/ci; Windows — windows-docs-host.json/windows-host.log рядом. GitHub Docs/полный Offline нового SHA проверяются после push, до land.
