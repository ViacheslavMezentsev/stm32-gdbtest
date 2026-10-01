# F411 CMSIS: тактирование, GPIO, SysTick и TIM2

[Документация](index.md) · [English](../en/F411_CMSIS_BASELINE.md)

01.10.2026, рабочая копия codex/f411-cmsis-baseline от main d97903c.
WeAct BlackPill F411CE + ST-Link/SWD, OpenOCD 0.12.0, Windows,
GCC 13.3.1-1.1/GDB 14.2.90. Без UART и внешней проводки.
SHA базы не обозначает SHA изменённых исходников. API/схемы и версия rc.2 не меняются.

## Реализация и проверки

Источник конфигурации: [RM0383](https://www.st.com/resource/en/reference_manual/dm00119316-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf), RCC/GPIO/TIM2.

HSI 16 МГц, SYSCLK/AHB/APB1/APB2 без делителей, PLL отключён после переключения.
SystemCoreClock=16000000, SysTick LOAD=15999; ISR увеличивает board_ticks_ms.
Интервал LED — 500 firmware ms через board_delay_ms/WFI, вместо busy loop.
PC13 — push-pull, low speed, no pull; исходный High соответствует выключенному LED.
F103 использует активный High PB2 и HSI 8 МГц: его численные ожидания не копируются.

TIM2 тактируется от APB1 16 МГц, PSC=15999, ARR=99 — номинально 100 мс.
После UG очищается UIF; IRQ28/vector44 публикует board_timer_events.
Статус UIF очищается rc_w0, без read-modify-write. Startup содержит SysTick и TIM2 vectors.

| HW_CI_* | Доказательство |
| --- | --- |
| BOOT | .data delay=500, BSS counters=0 при main, продвижение app_loop |
| GPIO | Clock PC13, mode/type/speed/pull и исходный High |
| CLOCK | HSI/SWS, делители, SystemCoreClock, SysTick LOAD/CTRL |
| BLINK | Чередование PC13 через ≥500 firmware ticks |
| TIM2_INIT | Clock, PSC/ARR, DIER/CR1/SMCR, NVIC и vector44 |
| TIM2_IRQ | Естественные exception44 с UIF, event++ и возврат в поток |
| SYSTICK_IRQ | Естественные exception15, tick++ и возврат в поток |

Контракты -g3 проверяют CMSIS-макросы в board.c; GDB читает exception через
SCB ICSR, без предположения об имени xPSR. Применены [TECH-001/002/003](TESTING_TECHNIQUES.md).
**7/7 HW PASS**, затем восстановлена исходная HAL-прошивка потребителя:
HW_BOOT/HW_BLINK PASS, reset_run. MCU оставлен работающим. Другие платы не запускались.

ELF SHA256: `2a5dad68f9832692cde09c993796bb4ce617fb7c851903d1594bba593988d58d`.
Артефакты: build/f411-cmsis-baseline/f411-windows-full-20261001T110610Z/summary.json,
JSON/JUnit по ссылкам summary; tested-source-hashes.json фиксирует исходники.
Build и артефакты в Git не включаются. Windows prepare/traceability: 8/8 PASS.

## Повтор и ограничения

Из tests/firmware: presets f411ce и f411ce-offline. Из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f411ce/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать F411/OpenOCD явно. После серии в finally вернуть HAL и проверить HW_BOOT/HW_BLINK.

Счётчики и интервалы подтверждены относительно firmware ticks, не независимого
эталона времени. GDB halt меняет тайминг; GPIO-регистр не доказывает световой поток.
WFI используется приложением, но interrupted WFI/Sleep-проверка будет отдельной группой.
Отказы генератора, jitter, пропуск IRQ и абсолютная частота здесь не проверяются.
ADC/DMA/units/failures, затем RTC/Sleep/recovery — следующие две группы.
HAL callbacks/return codes не заменяются CMSIS-регистрами; приёмы HAL остаются в руководстве.
GitHub Docs/Offline проверяются отдельно после push; gitlink потребителя пока на rc.2.

Локально Windows docs/host4/4 (98 unittest, 8 платформенных skips), формат C/H PASS.
Linux Docker host и девять MCU/GCC сочетаний — 10/10 PASS; логи в
build/f411-cmsis-baseline/linux-source/build/ci. Это offline-проверки, не Linux HW.
