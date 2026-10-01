# F429 CMSIS: ADC, DMA, арифметика и отказы

[Документация](index.md) · [English](../en/F429_CMSIS_ADC_DMA.md)

01.10.2026, рабочая копия codex/f429-cmsis-adc-dma от main `7a261e8`.
STM32F429I-DISCO + встроенный ST-Link/V2, CN1/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Продолжение [baseline](F429_CMSIS_BASELINE.md).

## Настройка и источники ожиданий

ADC1 scan CH18 температуры и CH17 VREFINT. PCLK2/2=8 МГц,
480 cycles (60 мкс), TSVREFE без VBAT, ADON/DMA/DDS; после power-up задержка 2 мс.
DMA2 stream0/channel0: два halfword в SRAM, normal/direct, IRQ56/vector72.
TC публикует raw до счётчика завершений; stream flags очищаются записью LIFCR.
Новый набор не использует F1-процедуру калибровки ADC.

Калибровки сверены с stm32f4xx_ll_adc.h из CubeF4 V1.28.3: TS_CAL1/2
30/110°C и VREFINT_CAL при 3.3 В по адресам 0x1FFF7A2C/2E/2A.
Условная ветка STM32F429xx использует CH18 с маршрутизацией температуры/VBAT;
VBAT выключен. IRQ56 сверен с stm32f429xx.h и HAL-профилем потребителя.
Firmware использует только CMSIS, общий adc_convert_f4_factory не изменён.
Quality2 означает происхождение калибровки, не точность температуры.

Буфер из двух halfword проверяется целиком в 0x20000000..0x2002FFFF.
CCM не включена в linker и недоступна DMA; это отдельное ожидание сценария,
а не только сравнение M0AR с символом. Драйвер находится в adc_f429.c.

После baseline HSI16 МГц ADC работает на 8 МГц вместо прежних HAL4 МГц. DMA остаётся normal, но DDS включён; перед каждым программным запуском driver заново включает DMA-запросы ADC и задаёт NDTR=2. Поэтому проверяется самостоятельный CMSIS-механизм, а не побитовое совпадение HAL-конфигурации.

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
Исходная HAL F429 восстановлена, HW_BOOT/HW_BLINK PASS, MCU оставлен running.
Один пример измерения: VDDA 2962 мВ, температура 29340 м°C, quality2; это не метрология.
Windows build и prepare/traceability16/16 PASS. Другие платы не запускались; общий converter не менялся.

ELF SHA256: `f3b5cee2c155a90d8339decb6cb80a8ba13489f0a5ac9d50fa1898df157b73a8`.
Артефакты build/f429-cmsis-adc-dma: f429-windows-full-20261001T143204Z/summary.json
и tested-source-hashes.json. SHA базы не обозначает изменённые исходники.
Presets f429zi/f429zi-offline из tests/firmware; CLI run с явным stand.
Внешний host timeout/recovery и full-image HW в этой группе не повторялись.
Следующая группа — RTC/Sleep/deadline/recovery; API/схемы/тег rc.2 неизменны.

Короткая серия без USB-сбоев не снимает исторического ограничения ST-Link/V2.

Локальная регрессия: Windows docs/host4/4 (98 unittest, 8 платформенных skips); Linux Docker format/host и 15 MCU/GCC сочетаний17/17 PASS. Логи: build/f429-cmsis-adc-dma/linux-source/build/ci; Windows — windows-docs-host.json/windows-host.log рядом. GitHub Docs/полный Offline нового SHA проверяются после push, до land.
