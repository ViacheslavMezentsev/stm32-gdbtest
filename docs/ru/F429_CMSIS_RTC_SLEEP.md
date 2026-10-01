# F429 CMSIS: RTC, Sleep, дедлайн и recovery

[Документация](index.md) · [English](../en/F429_CMSIS_RTC_SLEEP.md)

01.10.2026, рабочая копия codex/f429-cmsis-rtc-sleep от codex/f429-cmsis-adc-dma `52c49fd`.
STM32F429I-DISCO + ST-Link/V2, CN1/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Без UART и дополнительной проводки.
Продолжение [baseline](F429_CMSIS_BASELINE.md) и [ADC/DMA](F429_CMSIS_ADC_DMA.md).
SHA базы не идентифицирует изменённый код; API, схемы и тег rc.2 не меняются.

## Реализация

RTC F429 использует календарь и Alarm A, LSI и PRER127/249.
Ожидания сверены с CMSIS STM32F429xx из CubeF4 V1.28.3 и прежним HAL-профилем.
Регистры RTC/EXTI17 и IRQ41 совместимы с общей реализацией rtc_f4.c;
её алгоритм не изменён. Векторы F401/F411/F429 объединены: RTC IRQ41/vector57,
DMA2 stream0 IRQ56/vector72. F401/F411 проверяются offline, аппаратная серия — только F429.
Ветка зависимая: сначала land ADC/DMA52c49fd, затем RTC/Sleep после её собственного CI.

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
MCU оставлен работающим. DEV_ID0x419 и Flash2048 КиБ соответствуют профилю этого экземпляра.

ELF SHA256: `c15e52f39b4d8669bfe2a12c20db78b0b308c61be554381a70739fa30aa20956`.
Артефакты в build/f429-cmsis-rtc-sleep (не коммитятся):

- f429-windows-full-20261001T151255Z/summary.json: 20 сценариев, пять повторов, два restore;
- f429-windows-full-20261001T151430Z/recovery-summary.json: timeout, RTC/ADC и два restore;
- tested-source-hashes.json: хеши исходников; пути JSON/JUnit/marker указаны в summary.

Windows build и prepare/traceability 21/21 PASS. Локальные Windows docs/host — 4/4 PASS
(98 host-тестов, 8 пропущены). Linux Docker: 17/17 PASS — форматирование, host
и пять MCU на GCC 13/14/15 (15 сочетаний сборки и prepare). Это offline-регрессия;
аппаратные результаты этой серии относятся только к F429/OpenOCD на Windows.
Сводки: `build/f429-cmsis-rtc-sleep/windows-docs-host.json` и
`build/f429-cmsis-rtc-sleep/linux-source/build/ci/summary.json`.

## Повтор и ограничения

Presets f429zi/f429zi-offline из tests/firmware. Из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f429zi/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать F429/OpenOCD явно. После RTC_DEADLINE повторить RTC/ADC,
после всей серии в finally восстановить HAL и проверить HW_BOOT/HW_BLINK.

Sleep здесь обычный WFI, не Stop/Standby, не измерение тока или времени сна.
RTC как источник пробуждения отдельно не изолировался. GDB halt влияет на время.
Инъекция mask проверяет дедлайн, не физический отказ LSI; остальные RTC wait faults
и несовместимый source не инжектировались. Не проверялись backup retention,
точность LSI, HAL callbacks, full-image и Linux HW. Для firmware deadline нужен SysTick;
внешний host timeout — независимая защита. Пять CMSIS-профилей теперь имеют аппаратные протоколы;
итоговая сверка HAL→CMSIS и перевод F411-consumer ещё впереди;
завершение этой группы не разрешает удаление HAL-профилей потребителя.
GitHub Docs/полный Offline опубликованного SHA проверяются отдельно перед land.


В этой серии USB-сбоев не было; историческое ограничение ST-Link/V2 не закрывается коротким PASS.
