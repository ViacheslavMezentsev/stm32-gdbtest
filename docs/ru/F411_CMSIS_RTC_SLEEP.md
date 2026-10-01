# F411 CMSIS: RTC, Sleep, дедлайн и recovery

[Документация](index.md) · [English](../en/F411_CMSIS_RTC_SLEEP.md)

01.10.2026, рабочая копия codex/f411-cmsis-rtc-sleep от main4a6f5d3.
WeAct BlackPill F411CE + ST-Link/SWD, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90. Без UART/внешней проводки.
Продолжение [baseline](F411_CMSIS_BASELINE.md) и [ADC/DMA](F411_CMSIS_ADC_DMA.md).
SHA базы не обозначает SHA изменённого кода; API/схемы/тег rc.2 не меняются.

## Реализация

RTC F411 использует календарь и Alarm A, в отличие от счётчика F103.
LSI номинально32 кГц, PRER127/249; источник —
[RM0383](https://www.st.com/resource/en/reference_manual/dm00119316-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).
Сценарий владеет календарём: init устанавливает время/дату fixture, все поля
Alarm A маскированы, событие происходит каждую календарную секунду.
Это не точная секунда внешнего времени и не проверка сохранения календаря.

BDRST не применяется; несовместимый уже выбранный RTC source даёт error2.
DBP/LSIRDY/ALRAWF/INITF/RSF имеют ожидания с дедлайном1000 SysTick ticks
(error1/3/4/5/6). WPR открывается на время настройки и закрывается.
ALRAF очищается rc_w0 с сохранением остальных флагов и INIT=0;
EXTI17 PR — W1C без read-modify-write. Alarm IRQ41/vector57 увеличивает счётчик событий.
В отличие от F103, программное перевооружение каждого alarm не требуется.

## Сценарии

| HW_CI_* | Доказательство |
| --- | --- |
| RTC_INIT | LSI/PRER, Alarm A, RSF/INIT, EXTI17 rising, NVIC bank1 и vector57 |
| RTC_ALARM | Два естественных exception57 с ALRAF/EXTI pending, event++ и возврат в поток |
| RTC_DEADLINE | mask=0 в LSIRDY wait: error3 через ≥1000 ticks без изменения backup configuration |
| SLEEP_SYSTICK | Оба NVIC banks маскируются; exception15 и interrupted PC после WFI; delay/ADC сохранены |
| SLEEP_TIM2 | Только IRQ28, SysTick остановлен: exception44 после WFI, ticks не растут; управление восстановлено |

[TECH-002/003/005/008](TESTING_TECHNIQUES.md): CMSIS frame, естественные IRQ,
инъекция аргумента и unwind interrupted frame с ограниченными попытками.
GDB может вставить signal trampoline; отсутствие unwind — ошибка, не PASS.
После перехода в app.c используются заранее сохранённые адрес/маска ICSR.

## Результат

**20/20 HW PASS**; три ADC_DMA повтора после ADC-инъекций и RTC_ALARM/ADC_DMA
после RTC_DEADLINE — ещё **5/5 PASS**. HAL восстановлена: HW_BOOT/HW_BLINK PASS.
Отдельный сценарий дошёл до app_loop, сохранил marker и завис в Python sleep;
внешний timeout дал ожидаемый ERROR/TimeoutExpired и reset_run (host recovery).
После него RTC_ALARM/ADC_DMA PASS, затем повторный HAL restore/boot/blink PASS.
MCU оставлен работающим. Другие платы не запускались.

ELF SHA256: `6411cb5136564a1b2cd6a167c1de5017d30ef0080d63efd600bd28a1391427dc`.
Локальные артефакты в build/f411-cmsis-rtc-sleep:
- f411-windows-full-20261001T114734Z/summary.json: полный набор, повторы и restore;
- f411-windows-full-20261001T114912Z/recovery-summary.json: внешний timeout и восстановление;
- tested-source-hashes.json: исходники. JSON/JUnit/marker указаны в summary.

Windows prepare/traceability21/21 PASS. Артефакты не коммитятся.

## Повтор и ограничения

Presets f411ce/f411ce-offline из tests/firmware. Из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f411ce/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать F411/OpenOCD явно; после RTC_DEADLINE повторить RTC/ADC,
после всей серии в finally восстановить HAL и проверить HW_BOOT/HW_BLINK.

Sleep здесь обычный WFI, не Stop/Standby, не ток или residency. RTC как источник
пробуждения отдельно не изолировался. GDB halt влияет на календарь и задержки.
Инъекция mask проверяет дедлайн, не физический отказ LSI; остальные RTC wait faults
и смена несовместимого source не инжектировались. Нет проверки backup retention,
точности LSI или HAL callbacks. SysTick нужен для firmware deadline;
внешний host timeout — отдельная защита. Pack/full-image и Linux HW не повторялись.
После land — сверка переноса трёх CMSIS fixtures и обновление gitlink потребителя;
это ещё не разрешение удалить прежние HAL-профили. CI опубликованного SHA проверяется отдельно.

Локальная регрессия: Windows docs/host4/4 (98 unittest,8 платформенных skips),
формат C/H PASS; Linux Docker host и девять MCU/GCC сочетаний10/10 PASS.
Логи: build/f411-cmsis-rtc-sleep/linux-source/build/ci.
