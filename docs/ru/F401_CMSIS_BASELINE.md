# F401 CMSIS: clocks, GPIO, SysTick и TIM2

[Документация](index.md) · [English](../en/F401_CMSIS_BASELINE.md)

01.10.2026, рабочая копия `codex/f401-cmsis-baseline` от main `591c096`.
WeAct BlackPill v3.0, маркировка STM32F401CCU6, ST-Link/SWD, OpenOCD0.12.0,
Windows/GCC13.3.1-1.1/GDB14.2.90. Плата заменена владельцем; UART не нужен.

## Профиль и реализация

Flash256 КиБ, RAM64 КиБ; ожидаемый DEV_ID0x423. В этом опыте прочитаны именно
0x423 и 256 КиБ, identity.matches=true, warnings пуст. Исторические экземпляры
с другим DEV_ID не переоцениваются этим результатом. Существующая warn/strict
политика сохраняется; память не расширяется по обнаруженному идентификатору.

CMSIS device STM32F401xC из CubeF4 V1.28.3. GPIO/RCC/TIM2/SysTick используют
общую с F411 ветку board.c; startup F401 имеет собственный набор векторов до
IRQ28. Сверены CMSIS stm32f401xc.h и действующий профиль F401 потребителя.
ADC/RTC функции F411 не подключаются к F401, включая вызов ADC из app_loop.
Их каналы, калибровка и IRQ будут рассмотрены отдельно.

HSI16 МГц, AHB/APB1/APB2 /1; PC13 push-pull low-speed, начальный High, LED
active-low. SysTick reload15999, интервал LED500 firmware ticks. TIM2 internal
clock, PSC15999/ARR99: номинально100 мс. UG загружает prescaler, UIF очищается
до NVIC enable; ISR очищает UIF записью нуля и публикует счётчик событий.

## Проверки и соответствие

| Сценарии | Что подтверждается |
| --- | --- |
| BOOT, GPIO, CLOCK, BLINK | .data/BSS, переход в app_loop, регистры GPIO/RCC/SysTick, чередование PC13 |
| TIM2_INIT, TIM2_IRQ | PSC/ARR/NVIC/vector44, два естественных IRQ и возврат thread mode |
| SYSTICK_IRQ | vector15/exception15, счётчик ticks и возврат thread mode |

Сценарии основаны на принятом [F411 baseline](F411_CMSIS_BASELINE.md), используют
CMSIS-макросы в board.c и [TECH-001/002](TESTING_TECHNIQUES.md). Ожидания по
частоте/пинам/IRQ зафиксированы в requirements.md; это не вызовы HAL.
Для исходных HAL boot/clock/GPIO/blink/TIM2 сохраняется проверка конечного
состояния и IRQ; аргументы HAL, handles/callbacks и force_return не проверяются.

Windows build и prepare/traceability **8/8 PASS**; HW **7/7 PASS** через штатный
CLI, image_verified и reset_run во всех отчётах. Затем восстановлена исходная
HAL-прошивка F401, HW_BOOT/HW_BLINK PASS, MCU оставлен running.
ELF SHA256: `c6a5cb4f319ed0b0ff2640ec2578d5cc0df3af2f424807fe21d0b4ce4fbad784`.
Артефакты: build/f401-cmsis-baseline/f401-windows-full-20261001T130710Z/summary.json
и tested-source-hashes.json рядом. SHA базы не обозначает изменённые исходники.
Первая попытка локального harness завершилась до подключения из-за опечатки
f401ce в пути session; после исправления запущена приведённая серия.

Presets `f401cc`, `f401cc-offline` находятся в tests/firmware. Offline CI добавляет
F401 к трём предыдущим MCU на GCC13/14/15. Аппаратный workflow/run_hw.py пока
сохраняет прежний список трёх плат; для baseline используется обычный CLI run
с profile session и явно выбранным ST-Link stand. Автоматическая HW-матрица
F401, full-image, timeout/recovery и другие backend в этом этапе не проверялись.
Точность HSI, jitter/потери IRQ и изолированное пробуждение WFI не утверждаются.
Следующие группы: ADC/DMA/units/failures, затем RTC/Sleep/recovery.

Локальная регрессия: Windows docs/host4/4 (98 unittest, 8 платформенных skips); Linux Docker без сети format/host и 12 MCU/GCC сочетаний — 14/14 PASS. Отчёты: build/f401-cmsis-baseline/linux-source/build/ci/summary.json. GitHub Docs/полный Offline проверяются после push нового SHA, до land.
