# F030 CMSIS: TIM3 и IRQ

[Документация](index.md) · [English](../en/F030_CMSIS_TIMER.md)

Протокол этапа: числа тестов и планы ниже относятся к указанной ревизии.
Текущий состав — [STATUS](STATUS.md), подготовка выпуска — [rc.2](RC2_READINESS.md).

30.09.2026, `codex/f030-cmsis-timer` от `40fafac`. NUCLEO-F030R8,
родной ST-Link/SWD 1 МГц, OpenOCD 0.12.0, Windows, GCC13.3.1-1.1,
GDB14.2.90/Python3.11.4. UART/дополнительные соединения не используются.

## Реализация и доказательство

TIM3 — внутренний upcounter, PSC=7999, ARR=99 при APB=8 МГц (/1):
номинальный период 100 мс. UG загружает PSC; его UIF очищается до разрешения
IRQ. NVIC IRQ16 включён, слот32 таблицы векторов ведёт в TIM3_IRQHandler.
Обработчик очищает UIF записью нуля в бит без read-modify-write и увеличивает
счётчик периодических событий приложения board_timer_events.
Остальные внешние слоты до TIM3 ведут в Default_Handler; более поздние IRQ
ещё не представлены и не должны включаться до расширения таблицы.
SysTick и LED остаются как в [базовом этапе](F030_CMSIS_BASELINE.md).

- HW_CI_TIM3_INIT проверяет clock, PSC/ARR, SMCR, CR1, DIER, NVIC и вектор.
- HW_CI_TIM3_IRQ наблюдает три входа в аппаратный обработчик с IPSR=32 и UIF=1,
  два увеличения счётчика ровно на один, затем возврат в thread mode.
  Последний шаг позволяет выявить непрерывный IRQ при неочищенном UIF.
- Предыдущие BOOT/GPIO/CLOCK/BLINK повторены: **6/6 HW PASS**.

ELF SHA256: `4d410c04ae6aee1fa6347cc95cc68d3b2c7579281f3b01899a2056397d5c0342`.
Итоговые JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/, серия
20260930T131107…20260930T131117; логи build/f030-cmsis-timer/*-final.log.
После серии восстановлена HAL-прошивка потребителя: HW_BOOT PASS,
20260930T131120, teardown reset_run. MCU оставлен работающим.

## Сопоставление и ограничения

HW_TIM3_INIT → HW_CI_TIM3_INIT: сохраняются PSC/ARR и внутренний clock;
проверяется уже работающий таймер, а не состояние до HAL setup.
HW_TIM3_IRQ → HW_CI_TIM3_IRQ: сохраняется эффект периодического обработчика,
добавляются IPSR/вектор/thread progress; HAL handle/callback не проверяются.
Тест не вызывает EGR и не устанавливает NVIC pending. Остановки GDB могут
объединять события UIF; число входов не доказывает отсутствие потерь или
точный период. Счётчик событий — состояние приложения, не тестовый hook.
WFI может теперь пробуждаться также от TIM3; это ещё не отдельный тест Sleep.

Повтор: build preset f030r8, CTest f030r8-offline, затем штатный CLI
`python -B -m stm32_gdbtest run --session tests/firmware/build/f030r8/hwtest/session.json --test <ID> --stand <local.toml>`.
run_hw.py по-прежнему содержит прежние десять шагов BOOT/GPIO; новые сценарии
вызываются через CLI. ADC/DMA/RTC и HAL-specific fixtures остаются в плане.

Локальная offline-регрессия: F030 CTest 7/7; Windows host 96 (8 skips); Linux Docker docs/host и F030/F103/F411 × GCC13/14/15 — 13/13 PASS. Архив Git index извлечён на case-sensitive filesystem. Формат изменённых C-файлов и strict ТЗ: PASS.
