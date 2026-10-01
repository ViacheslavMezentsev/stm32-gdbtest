# F103 CMSIS: RTC, Sleep, дедлайны и восстановление

[Документация](index.md) · [English](../en/F103_CMSIS_RTC_SLEEP.md)

01.10.2026, рабочая копия codex/f103-cmsis-rtc-sleep от main 3e123ad.
WeAct BluePill-Plus F103C8, J-Link 8.32/SWD, Windows,
GCC 13.3.1-1.1/GDB 14.2.90. UART и внешние соединения не нужны.
Продолжение групп [baseline](F103_CMSIS_BASELINE.md) и [ADC/DMA](F103_CMSIS_ADC_DMA.md).
SHA базы не обозначает SHA изменённого кода; API и схемы модуля не изменены.

## RTC F1 и границы переноса

По [RM0008](https://www.st.com/resource/en/reference_manual/rm0008-stm32f103xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
RTC F103 — 32-битный счётчик, 20-битный prescaler и comparator Alarm.
У него нет календаря, PRER/ALRMAR и write-protection sequence F030.
Fixture выбирает LSI, PRL=39999 (номинально 1 с при 40 кГц), начинает счётчик с нуля
и назначает первый alarm=2. Она владеет счётчиком и теряет прежнее время,
но не делает BDRST. Другой уже выбранный RTC clock source отвергается с error2.

RSF синхронизирует APB shadow; RTOFF проверяется до/после конфигурации через CNF.
Ожидания ограничены 1000 firmware ticks: error1 — DBP, 3 — LSIRDY,
4 — RSF, 5 — готовность записи, 6 — завершение записи.
Флаги CRL очищаются по rc_w0 с сохранением остальных флагов и CNF=0;
EXTI17 PR очищается записью W1C, без read-modify-write.

Alarm поступает через EXTI17 rising, IRQ41/vector57. Глобальный RTC IRQ3 отключён.
ISR очищает флаги, увеличивает board_rtc_events и запрашивает перевооружение.
Основной поток через board_rtc_service читает согласованные CNTH/CNTL и ставит
следующий alarm на counter+2. Ожидания записи не выполняются внутри ISR:
иначе SysTick меньшего приоритета не мог бы обеспечивать дедлайн.
Это периодическое уведомление с задержкой обслуживания основным циклом,
не точный двухсекундный планировщик. Длительная остановка GDB меняет расписание.

## Сценарии и доказательства

| Сценарий HW_CI_* | Что проверено |
| --- | --- |
| RTC_INIT | LSI, PRL, первый alarm, RSF/RTOFF/CNF, EXTI17, NVIC и vector57 |
| RTC_ALARM | Два естественных IRQ57 с ALRF/EXTI pending, один event на IRQ, перевооружение и возврат в поток |
| RTC_DEADLINE | mask=0 в rtc_wait для LSIRDY: error3 через ≥1000 ticks, backup configuration сохранена |
| SLEEP_SYSTICK | External IRQ отключены в обоих NVIC banks; exception15, interrupted PC после WFI |
| SLEEP_TIM2 | Только IRQ28, SysTick остановлен: exception44 после WFI, ticks не растут, затем восстановление |

Сон проверяется через GDB unwind с ограниченными попытками и сохранением
interrupted_contexts. Это обычный Sleep, не Stop/Standby и не измерение тока.
Контекст макросов берётся из соответствующего CMSIS translation unit;
адрес ICSR сохраняется до перехода в HAL-free app.c.
Использованы [TECH-002/003/005/008](TESTING_TECHNIQUES.md).

**20/20 HW PASS**, включая всю предыдущую регрессию; **5/5 положительных повторов**:
ADC_DMA после трёх ADC-инъекций, RTC_ALARM и ADC_DMA после RTC_DEADLINE.
Итог первого harness отмечен ERROR: восстановление HAL не смогло создать
каталог отчёта из-за Windows sandbox ACL. Перенос отчёта оставил вторую ошибку
доступа к старому probe-lock. Обе ошибки возникли до подключения к MCU и сохранены.
Отдельный запуск восстановления с необходимым доступом: HW_BOOT/HW_BLINK PASS.

Дополнительно сценарий дошёл до app_loop, записал marker и намеренно завис
в Python sleep. Внешний timeout дал ожидаемый ERROR/TimeoutExpired,
`reset_run (host recovery)`; после него RTC_ALARM и ADC_DMA PASS.
HAL восстановлена повторно, HW_BOOT/HW_BLINK PASS; MCU оставлен работающим.

ELF SHA256: `07647c3c0bac19367645325c61ffc5886c648e04f8f0d15f463a4a94fbcf1315`.
Локальные артефакты в build/f103-cmsis-rtc-sleep:
- f103-windows-full-20261001T103058Z/summary.json: 25 PASS, ошибка restore;
- f103-windows-full-20261001T103225Z/restore-summary.json: ошибка доступа к lock;
- f103-windows-full-20261001T103241Z/restore-summary.json: успешное восстановление;
- f103-windows-full-20261001T103317Z/recovery-summary.json: timeout/recovery и окончательное восстановление.

JSON/JUnit и marker сохраняются в каталогах, указанных summary.
tested-source-hashes.json фиксирует исходники; артефакты игнорируются Git.

## Повтор и ограничения

Сборка/prepare: presets f103c8 и f103c8-offline в tests/firmware.
Запуск из корня модуля:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f103c8/hwtest/session.json --test <ID> --stand <local.toml>`.
Выбирать BluePill/J-Link явно. После RTC_DEADLINE повторить RTC_ALARM/ADC_DMA;
после серии восстановить HAL потребителя и проверить HW_BOOT/HW_BLINK в finally.

Инъекция mask проверяет алгоритм дедлайна, не физический отказ LSI.
RSF/RTOFF/DBP и несовместимый clock source не инжектировались; backup retention,
переполнение счётчика, точность LSI и Sleep от RTC отдельно не подтверждены.
Базовый тайм-аут зависит от работающего SysTick; внешний host timeout — отдельная защита.
Нет доказательства HAL callbacks/return codes; прежние HAL-приёмы не заменяются этими тестами.
Pack/full-image и Linux HW в этой группе не повторялись. Остальные платы не запускались.

Windows prepare/traceability: 21/21 PASS, docs/host: 4/4 (98 unittest,
8 платформенных skips). Linux Docker host и девять сочетаний F030/F103/F411 ×
GCC13/14/15: 10/10 этапов PASS; логи linux-source/build/ci внутри каталога опыта.
Формат собственных C/H — PASS. GitHub Docs/Offline проверяются после push.
