# F103 CMSIS: clocks, GPIO, SysTick и TIM2

[Документация](index.md) · [English](../en/F103_CMSIS_BASELINE.md)

01.10.2026, ветка codex/f103-cmsis-baseline от a0d6547 (rc.2).
Проверялась рабочая копия ветки; SHA базы не объявляется SHA нового кода.
WeAct BluePill-Plus STM32F103C8T6, J-Link/SWD, Windows, GCC 13.3.1-1.1,
GDB 14.2.90, J-Link GDB Server 8.32. UART и внешняя проводка не нужны.

## Реализация и сценарии

Одна группа объединяет clocks/SysTick, GPIO/blink, TIM2 и IRQ. HSI 8 МГц,
AHB/APB1/APB2 /1, SysTick 1 мс, PB2 initially Low, переключение через 500 мс.
TIM2: PSC=7999, ARR=99, номинально 100 мс. UG загружает PSC, UIF очищается до
разрешения IRQ; обработчик очищает UIF без read-modify-write и публикует событие.
Счётчики являются состоянием приложения; тестовых hooks нет.

| Сценарий | Доказательство |
| --- | --- |
| HW_CI_BOOT | .data/BSS и продвижение app_loop |
| HW_CI_GPIO | APB2 clock, PB2 push-pull 2 МГц, исходный Low |
| HW_CI_CLOCK | HSI ready/source, делители, SystemCoreClock, SysTick LOAD/CTRL |
| HW_CI_BLINK | Чередование PB2, не менее 500 firmware ticks между переключениями |
| HW_CI_TIM2_INIT | PSC/ARR/SMCR/CR1/DIER, NVIC IRQ 28 и vector 44 |
| HW_CI_TIM2_IRQ | Естественный exception 44/UIF, два приращения счётчика, thread progress |
| HW_CI_SYSTICK_IRQ | Естественный exception 15, vector 15, приращение ticks, thread progress |

Применены [TECH-001/002](TESTING_TECHNIQUES.md): физические ожидания отдельно от
CMSIS-выражений; вычисление макросов в board.c, где подключён device header.
GPIO F1 использует APB2/CRL, а не AHB/MODER как F0/F4. Проверка CEN выполняется
на уже запущенном таймере, не до HAL setup. HAL callbacks/handles/force_return
этой группой не покрываются и сохраняются в HAL-регрессии.

## Аппаратная проверка

**7/7 PASS**, затем исходная HAL-прошивка потребителя восстановлена:
HW_BOOT/HW_BLINK PASS, teardown reset_run. MCU оставлен running.
ELF SHA256: `29d83ac6a6e67276d713776a27fb2992ec1fa6f60639555491452a1e48d05ba7`.
Локальное доказательство: build/f103-cmsis-baseline/
f103-windows-full-20261001T074519Z/summary.json; JSON/JUnit —
tests/firmware/build/f103c8/hwtest/runs. Summary содержит ссылки на отдельные отчёты.

Первый запуск 074453: BOOT PASS, GPIO ERROR — в сценарии осталось имя
RCC_AHBENR_GPIOBEN от другого семейства. HAL восстановлен и проверен даже при
ошибке. Исправлено выражение на RCC APB2/IOPBEN, firmware не менялась; полный
повтор указан выше. Контракт проверял правильные имена, но не неуказанное
ошибочное выражение: успешный prepare не доказывает корректность всего сценария.

## Ограничения и повтор

Остановки GDB влияют на время; IRQ pending/UIF могут объединять события.
Сценарии не доказывают точность HSI, джиттер, отсутствие потерянных событий или
видимое свечение LED. Векторы внешних IRQ определены только до TIM2 (IRQ 28);
до включения следующих IRQ расширить startup. WFI используется задержкой,
но отдельная проверка Sleep/residency сюда не входит. ADC/DMA и RTC — следующие группы.

Из tests/firmware: cmake --preset f103c8, cmake --build --preset f103c8,
ctest --preset f103c8-offline. Затем из корня модуля штатный CLI:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f103c8/hwtest/session.json --test <ID> --stand <local.toml>`.
Перед HW выбрать BluePill/J-Link и подготовить restore-session потребителя.
run_hw.py проверяет lifecycle через boot/GPIO, а не все семь сценариев.

Offline: Windows F103 CTest 8/8 (семь prepare + traceability), host98
(8 платформенных skips). Linux Docker: host и F030/F103/F411 × GCC13/14/15,
10/10 этапов PASS, включая отрицательные contracts и image policy.
Отчёт: build/f103-cmsis-baseline/linux-source/build/ci/summary.json.
Другие платы аппаратно в этой группе не проверялись.
