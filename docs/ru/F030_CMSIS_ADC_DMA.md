# F030 CMSIS: ADC/DMA и таймаут завершения

[Документация](index.md) · [English](../en/F030_CMSIS_ADC_DMA.md)

30.09.2026, ветка codex/f030-cmsis-adc-dma от 5883316. NUCLEO-F030R8,
штатный ST-Link V2J45M31/SWD 1 МГц, OpenOCD0.12.0, Windows,
xPack GCC13.3.1-1.1/GDB14.2.90/Python3.11.4. Только USB/SWD, без UART
и внешних аналоговых сигналов. Реализация — tests/firmware/src/adc_f030.c.

## Что перенесено

ADC1: асинхронный HSI14, калибровка при выключенном ADC и без DMA-запросов,
12 бит, forward scan каналов16/17 (температура/VREFINT), sampling239.5,
одна последовательность программного запуска на цикл приложения.
Внутренним источникам и переходу после калибровки даны две границы SysTick,
то есть минимум один полный миллисекундный интервал независимо от фазы.
DMA1 channel1: normal, halfword, MINC, два отсчёта в SRAM, TC/TE IRQ9.
Обработчик публикует пару raw перед увеличением board_adc_sequences.

Штатные ожидания HSI14/calibration/ADRDY/публикации ограничены 20 отсчётами
SysTick. Коды board_adc_error: 1 clock, 2 calibration, 3 ready,
4 completion timeout, 5 DMA transfer error, 6 busy ADC. board_adc_fault
останавливает DMA и остаётся в WFI; автоматического retry нет.
Дедлайн зависит от исправного SysTick; внешний timeout runner сохраняется.

## Проверки и результаты

| Сценарий | Доказательство |
| --- | --- |
| HW_CI_ADC_INIT | Clock, CKMODE, scan, sampling, internal paths, calibration finished/ADEN, DMA адреса/формат, NVIC и вектор25 |
| HW_CI_ADC_DMA | Две последовательности: IPSR25, TCIF без TEIF, CNDTR0, публикация двух raw и sequence, отсутствие overrun |
| HW_CI_ADC_TIMEOUT | Отключён IRQ9 через журналируемую NVIC mutation; DMA завершён, publication0, error4 и board_adc_fault |

Итог **9/9 HW PASS**, включая шесть прежних сценариев; серия
20260930T135918…20260930T135934. Наблюдались raw пары (1759,1519),
(1758,1519); это наблюдения этого экземпляра, не точные физические ожидания.
ELF SHA256: `9200ea94e66d7e69792336eca76f38a24158fbdfb1a63a16be220bf03e3b91ab`.
JSON/JUnit — tests/firmware/build/f030r8/hwtest/runs/;
логи — build/f030-cmsis-adc-dma/*-final.log. HAL-прошивка восстановлена,
HW_BOOT PASS 20260930T135936, reset_run; MCU работает.

Первый опыт остановился на HW_CI_ADC_INIT: CFGR2 прочитан как 0x1000 вместо
полного нуля. Тест неверно включал биты вне CKMODE. Сверено с CMSIS F0
V1.11.6: выбор clock задаёт маска ADC_CFGR2_CKMODE (31:30). Исправлено только
ожидание поля, не конфигурация. FAIL и промежуточные отчёты сохранены.
Правило: сравнивать документированное поле по CMSIS-маске, не требовать
нулей от всех остальных битов регистра. ADC DR тестами не читается.

## Границы и следующие шаги

HW_ADC_DMA_INIT/RUNTIME заменяются CMSIS-настройкой и реальной DMA-публикацией.
HW_ADC_DMA_TIMEOUT заменён отсутствующим IRQ; HAL callback suppression и
HAL_ADC_Start_DMA error return здесь не проверяются и требуют отдельной fixture.
Не проверены остальные пять кодов отказа, точность ADC, температура/VDDA в
физических единицах и внешние каналы. Следующий этап — single-point калибровка
F030 и независимые арифметические векторы; не читать TS_CAL2 по общему header.
Влияние остановок GDB не позволяет выводить throughput/потребление.
F103/F411, API ядра и старые десять шагов run_hw.py не изменены.
Новые сценарии доступны обычным CLI run --test и входят в CI prepare.

Первый Docker-прогон: 10/13, F030 отклонён строгой проверкой списка translation units после добавления adc_f030.c. Ожидаемый список дополнен только для F030, диагностика отсутствующего linker input отделена от несовпадения sources.

Проверки: Windows host 96 (8 skips); F030 CTest 10/10; Linux после исправления — docs и F030 × GCC13/14/15 6/6 PASS. F103/F411 × три GCC и Linux host прошли в первом прогоне. Полная матрица подтверждена двумя прогонами, не одним 13/13. Формат и strict ТЗ PASS. Архив Git index извлечён на case-sensitive filesystem.
