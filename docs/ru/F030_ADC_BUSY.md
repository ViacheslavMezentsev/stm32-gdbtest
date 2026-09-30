# F030: отказ запуска занятого ADC

[Документация](index.md) · [English](../en/F030_ADC_BUSY.md)

Ветка codex/f030-adc-busy от 5d09823, первая в пакете из трёх.
Firmware и ядро не изменены. Тест HW_CI_ADC_BUSY включает CONT и ADSTART
перед первым board_adc_sample через журналируемые MMIO-записи, подтверждает
ADSTART, затем требует board_adc_error=6 в board_adc_fault. Sequence и quality
остаются нулевыми. Поток намеренно не считывается; overrun ожидаем.
Teardown reset_run возвращает обычную конфигурацию. Это занятый ADC, а не
подмена HAL_ADC_Start_DMA; отказ DMA и все причины аппаратных ошибок не покрыты.

NUCLEO-F030R8/ST-Link V2J45M31, SWD1MHz/OpenOCD0.12.0, GCC13/GDB14.2.90,
Windows: HW PASS 20260930T172928. Предыдущие 16 сценариев в этой ветке не повторялись.
ELF тот же, что в [RTC-протоколе](F030_CMSIS_RTC.md).
F030 build/prepare/traceability 18/18, Windows host 96 (8 skips) PASS.
Отчёт: tests/firmware/build/f030r8/hwtest/runs/; лог: build/f030-fault-batch/adc-busy.log.
Следующая зависимая ветка — RTC deadline; затем общая приёмка и восстановление HAL.
