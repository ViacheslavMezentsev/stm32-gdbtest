# F401 CMSIS: RTC, Sleep, дедлайн и recovery

[Документация](index.md) · [English](../en/F401_CMSIS_RTC_SLEEP.md)

01.10.2026, рабочая копия codex/f401-cmsis-rtc-sleep от main `87a23be`.
WeAct BlackPill v3.0 STM32F401CCU6 + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Без UART и дополнительной проводки.
Продолжение [baseline](F401_CMSIS_BASELINE.md) и [ADC/DMA](F401_CMSIS_ADC_DMA.md).
SHA базы не идентифицирует изменённый код; API, схемы и тег rc.2 не меняются.

## Реализация

RTC F401 использует календарь и Alarm A. LSI номинально 32 кГц, PRER127/249;
источник ожиданий — [RM0368](https://www.st.com/resource/en/reference_manual/DM00096844.pdf)
и CMSIS STM32F401xC из CubeF4 V1.28.3. Регистры RTC, EXTI17 и IRQ41 совпадают
с использованными в F411: реализация rtc_f411.c перенесена в общий rtc_f4.c.
Векторы F401/F411 объединены: RTC IRQ41/vector57 и DMA2 stream0 IRQ56/vector72.
F411 после этого изменения проверен offline; новая аппаратная серия относится только к F401.

Пример владеет календарём: при инициализации устанавливает начальную дату/время
и маскирует поля Alarm A для события каждую календарную секунду. BDRST не используется;
несовместимый уже выбранный источник даёт error2. Ожидания DBP/LSIRDY/ALRAWF/INITF/RSF
ограничены 1000 SysTick ticks (error1/3/4/5/6). ALRAF очищается rc_w0, EXTI PR — W1C.
Это не проверка точности часов или сохранения календаря после сброса.

## Сценарии

| HW_CI_* | Доказательство |
| --- | --- |
| RTC_INIT | LSI/PRER, Alarm A, RSF/INIT, EXTI17 rising, NVIC bank1 и vector57 |
| RTC_ALARM | Два естественных exception57 с ALRAF/EXTI pending, event++ и возврат в поток |
| RTC_DEADLINE | mask=0 в LSIRDY wait: error3 через ≥1000 ticks без изменения backup configuration |
| SLEEP_SYSTICK | Оба NVIC banks маскируются; exception15 и interrupted PC после WFI; delay/ADC сохранены |
| SLEEP_TIM2 | Только IRQ28, SysTick остановлен: exception44 после WFI, ticks не растут; управление восстановлено |

[TECH-002/003/005/008](TESTING_TECHNIQUES.md): контекст CMSIS, естественные IRQ,
инъекция аргумента и ограниченное число попыток unwind interrupted frame.
GDB может вставить signal trampoline; отсутствие unwind — ошибка, не PASS.
После перехода в app.c используются заранее сохранённые адрес/маска ICSR.

## Результаты

**20/20 HW PASS**, ещё **5/5 PASS**: три ADC_DMA после ADC-инъекций и RTC_ALARM/ADC_DMA
после RTC_DEADLINE. HAL восстановлена, HW_BOOT/HW_BLINK PASS.
Отдельный сценарий дошёл до app_loop, сохранил marker и завис в Python sleep.
Внешний timeout дал ожидаемый ERROR/TimeoutExpired и reset_run (host recovery).
RTC_ALARM/ADC_DMA после него PASS; повторный HAL restore/boot/blink PASS.
MCU оставлен работающим. DEV_ID0x423 и Flash256 КиБ соответствуют профилю этого экземпляра.

ELF SHA256: `9d9ab4ac8f8593be5bdfcacac3493e6f81bb66309fb8d258f8d764dc25047830`.
Артефакты в build/f401-cmsis-rtc-sleep (не коммитятся):

- f401-windows-full-20261001T134226Z/summary.json: 20 сценариев, пять повторов, два restore;
- f401-windows-full-20261001T134412Z/recovery-summary.json: timeout, RTC/ADC и два restore;
- tested-source-hashes.json: хеши исходников; пути JSON/JUnit/marker указаны в summary.

Windows build и prepare/traceability21/21 PASS.

## Повтор и ограничения

Presets f401cc/f401cc-offline из tests/firmware. Из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f401cc/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать F401/OpenOCD явно. После RTC_DEADLINE повторить RTC/ADC,
после всей серии в finally восстановить HAL и проверить HW_BOOT/HW_BLINK.

Sleep здесь обычный WFI, не Stop/Standby, не измерение тока или времени сна.
RTC как источник пробуждения отдельно не изолировался. GDB halt влияет на время.
Инъекция mask проверяет дедлайн, не физический отказ LSI; остальные RTC wait faults
и несовместимый source не инжектировались. Не проверялись backup retention,
точность LSI, HAL callbacks, full-image и Linux HW. Для firmware deadline нужен SysTick;
внешний host timeout — независимая защита. F429 CMSIS ещё предстоит перенести;
завершение этой группы не разрешает удаление HAL-профилей потребителя.
GitHub Docs/полный Offline опубликованного SHA проверяются отдельно перед land.

Локальная регрессия: Windows docs/host4/4 (98 unittest,8 платформенных skips), Linux Docker format/host и12 MCU/GCC сочетаний14/14 PASS. Логи: build/f401-cmsis-rtc-sleep/linux-source/build/ci; Windows — windows-docs-host.json/windows-host.log рядом.
