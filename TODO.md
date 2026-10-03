# Дорожная карта

## Исследование расширения API — 03.10.2026

- Продолжение F0/F1: по 8/8 HW PASS (baseline, E1–E4, BOOT/GPIO restore); stale ELF prepare ERROR сохранён, F1 Flash mismatch остаётся предупреждением. [Отчёт](docs/research/api-extension/ru/portability.md).
- По решению владельца создано [ТЗ API 0.1.0](docs/TECHNICAL_SPECIFICATION_API.md) для текущего rc.2, общее ТЗ 0.59 делегирует контракты. Три компонента относятся к ревизии документа; API_VERSION=1 и ядро прежние. Далее согласование контрактов расширения/Q1–Q16, не автоматический перенос.

- E5 завершён: [матрица соответствия](docs/research/api-extension/ru/e5.md) правилам E1–E12 и моделям трёх проектов; пакет целиком к переносу не готов. Рекомендация: сначала согласовать record/records; read/context доработать, finish оставить экспериментальным. Q1–Q16 открыты, E6 ждёт решения владельца; ядро и версии прежние.

- E4: ограниченный natural finish Cortex-M void/integer, host 44/44; F411 первый ERROR (истёкший объект точки), исправленный опыт 4/4 PASS, оба restore PASS. [Отчёт](docs/research/api-extension/ru/e4.md). Полный контракт/timeout/HW fault остаются долгом Q9–Q12; следующий этап E5, ядро не изменено.

- E3: минимальный context/stack и caller, host 36/36; F411 первый ERROR (константа GDB отсутствует), исправленный опыт и restore 4/4 PASS. Оба восстановления PASS, ERROR сохранён. [Отчёт](docs/research/api-extension/ru/e3.md); вопросы Q1–Q8 в конце плана, далее E4.

- E2: ограниченный read глобальных объектов RAM, типизированные неизменяемые снимки; host 29/29, F411 baseline/опыт/restore 4/4 PASS. [Отчёт](docs/research/api-extension/ru/e2.md). Эргономика, provenance/availability и frame остаются вопросами E3/E5; далее frames/context. HAL восстановлен, ядро прежнее.

- В конец плана добавлены E5 (сверка свойств с api-evolution/api-proposal/execution-context) и условный E6 (принятие API, версия, вопросы, ТЗ и миграция сценариев после согласования). Это не утверждение переноса в ядро.

- Текущая ветка: `codex/api-extension-research` от `b3d19e0`; GitHub main сверён через API и совпадает с базой.
- [План и результаты](docs/research/api-extension/ru/index.md): E1 record → E2 read → E3 frames/context → E4 finish; сравнение с текущими сценариями относительно rc.2.
- Подготовлены план RU/EN и пустой реестр запусков. Следующий шаг — контракт и изолированный прототип E1 record; экспериментальные прогоны ещё не выполнялись.
- Ядро и нормативное ТЗ не изменены; перенос требует отдельного утверждения. HW/RTOS первого исследования остаются на паузе.
- Проверка документации в Docker CI: docs 3/3 PASS (ТЗ, локальные ссылки, пары RU/EN).
- E1: изолированный runtime record/records, запросы Python и статистика VDDA/температуры; Windows host 19/19 PASS. [Отчёт](docs/research/api-extension/ru/e1.md). Следующий шаг — GDB/F411 и парное сравнение; экспорт вне объёма, HW ещё не запускалось.
- E1 HW продолжение: F411/OpenOCD/GDB14, 10 измерений VDDA/температуры, baseline/опыт/restore 4/4 PASS. Две ошибки подготовки сохранены; HAL восстановлен. Следующий шаг — парное сравнение ADC/HAL.
- E1 завершён: 22/22 host (22 парных набора в 3 новых тестах), ADC-пара F411 и восстановление 4/4 PASS. [Сравнение](docs/research/api-extension/ru/e1-comparison.md): длина сценариев прежняя, report исключён; польза — журнал/запросы. HAL-пара только host. Далее E2 read; ядро не изменено.

## Интеграция исследований в main — 03.10.2026

- По решению владельца объединены исследование GDB Python/API (`codex/rc3-api-r1`, `fffa11d`) и модель дерева (`codex/adaptive-test-tree`, исходный `25544d8`). Второе перенесено поверх первого с сохранением подписанных коммитов.
- Принято в локальный main перемоткой; исходные исследовательские ветки удаляются после проверки включения всех коммитов. Публикация в GitHub остаётся владельцу; fetch завершился connection reset, актуальность удалённого main не подтверждена.
- Проверки объединённого дерева: Docker docs/format/host 5/5 PASS; Windows host 112 тестов, 8 платформенных skips. Ядро stm32_gdbtest без изменений, HW не запускалось.
- Перенос экспериментальных средств в ядро не утверждён. HW/RTOS остаются на паузе, соглашения API — проект.
- Следующее возможное исследование: ресурсы, раздельные владение/физическое состояние, неподтверждённое освобождение и переключение обычных проверок на диагностику; YAML-каркас. Пока не реализовано.

## Сохранённое исследование: адаптивное дерево сценариев

- Исходная база модели: main `da42cd7`; при интеграции добавлено исследование GDB Python/API.
- [x] Только Python-имитация: дерево папок, вход/выход, All/Any/UNKNOWN, динамическая блокировка и реактивация, сохранение FAIL/ERROR.
- [x] Независимый JSON-эталон:8 полных снимков,7 исполнений;14 поведенческих тестов, отрицательный контроль испорченного движка.
- [x] Автономный [HTML-проигрыватель](docs/research/adaptive-test-tree/results/player.html): слайдер, Play/Pause, узлы и причины блокировки.
- [x] [План и отчёт RU/EN](docs/research/adaptive-test-tree/ru/index.md); API/ТЗ/производственный runner не изменены, HW не запускалось.
- [x] Windows host112 (8 skips), Linux host112 (4 skips); Docker docs/host4/4, модель14/14, воспроизводимость JSON/HTML и браузер проверены.
- [x] Workflow-карточки с раздельной доступностью/результатами и неподвижными связями; будущий YAML-каркас описан в плане RU/EN.
- [ ] Обсудить семантику модели и следующие эксперименты.

## Сохранённое исследование: соглашения об эволюции API и разделение ТЗ

- Ветка `codex/rc3-api-r1`, после `9ca1741`; ядро и публичный API не меняются.
- [x] Текущий цикл R1–R18 завершён с открытым долгом; аппаратные проверки не возобновляются.
- [x] Подготовлен [проект соглашений](docs/research/rc3-gdb-python/ru/api-evolution.md): E1–E12, разделение общего и API ТЗ, исходы операций и порядок перехода. Нормативные ТЗ пока прежние.
- [ ] Согласовать правила, владельцев требований и релизную цель rc3/0.2.0; затем подготовить отдельное ТЗ API и согласованную ревизию общего ТЗ по навыку.
- [x] R1–R18 сохранены отдельными RU/EN отчётами; [сводка](docs/research/rc3-gdb-python/ru/summary.md) связывает все результаты и ограничения.
- [x] Подготовлены [API → техники → шаблоны](docs/research/rc3-gdb-python/ru/scenario-tools.md), области применения и критерии будущего API.
- [x] Описан проект [контекста исполнения](docs/research/rc3-gdb-python/ru/execution-context.md), включая PC/SP, доступность и актуальность снимка. Не реализован.
- [x] 02.10.2026 владелец остановил RTOS и все оставшиеся HW-этапы: [общий технический долг](docs/research/rc3-gdb-python/ru/technical-debt.md). Исторические «следующие этапы» ниже не являются актуальной очередью запуска.
- [x] Подготовлен отдельный [черновик состава API](docs/research/rc3-gdb-python/ru/api-proposal.md): пакеты A/B/C, предварительные сигнатуры, результаты операций и открытые вопросы Q1–Q9.
- [x] В предложение добавлены операции со стеком/аргументами/locals, caller_is и поиск предка, неполнота unwind и граница между backtrace и деревом истории. Только документация; HW на паузе.
- [ ] Обсудить кандидатов и утвердить объём реализации; перенос в ядро только после отдельного утверждения владельца. HW не возобновлять без нового указания.
- Публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R18

- Ветка `codex/rc3-api-r1`, после `9890531`; перенос в ядро только после утверждения владельца.
- [x] C++/агрегаты soft/hard:48/48 finish/call/методы +24 PASS/6 FAIL structure-return, F411/HLA GDB14/16. FAIL сохранены: Pair soft/hard, HFA soft; Small и HFA hard проходят.
- [x] Проверены this, аргументы и выбор const-перегрузок, приёмники и естественное продолжение; ограничение R5 подтверждено. Default ELF прежний.
- [x] Restore HW_BOOT/HW_GPIO PASS во всех14 сериях. [RU](docs/research/rc3-gdb-python/ru/r18.md) / [EN](docs/research/rc3-gdb-python/en/r18.md).
- [x] Windows/Linux71/71 host/prepare для каждой ABI на каждой ОС; docs3/3, format1/1 на канонической копии.
- [ ] Следующий этап: RTOS — обычная прошивка, задачи, контекст и фильтры; затем надёжность по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R17

- Ветка `codex/rc3-api-r1`, после `0fd9f8c`; перенос в ядро только после утверждения владельца.
- [x] Scalar ABI soft/hard:48/48 F411/HLA GDB14/16; void/double/float/6 аргументов, finish/return/call и конечные приёмники.
- [x] FPU включена обычным main hard-сборки; double использует VFP ABI с программной арифметикой. Прежний Og ELF сохранился.
- [x] Restore HW_BOOT/HW_GPIO PASS в обеих матрицах, неожиданных FAIL/ERROR нет. [RU](docs/research/rc3-gdb-python/ru/r17.md) / [EN](docs/research/rc3-gdb-python/en/r17.md).
- [x] Windows/Linux65/65 host/prepare для каждой ABI на каждой ОС; docs3/3, format1/1 на канонической копии.
- [ ] Следующий подэтап ABI: структуры/HFA и C++; затем RTOS по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9). Исходный struct-return FAIL R5 остаётся открытым.
- Ядро/API прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R16

- Ветка `codex/rc3-api-r1`, после `d043fec`; перенос в ядро только после утверждения владельца.
- [x] until/advance/nexti:32/32 F411/HLA GDB14/16 на прежнем Og ELF; строки, выход кадра до цели и прерывание отдельной точкой.
- [x] Исходный ERROR чтения i вне области видимости сохранён; исправленная проверка отличает scope от optimized_out. Restore HW_BOOT/HW_GPIO PASS в обеих сериях. [RU](docs/research/rc3-gdb-python/ru/r16.md) / [EN](docs/research/rc3-gdb-python/en/r16.md).
- [x] Windows/Linux62/62 host/prepare, после исправления затронутые4/4 на каждой ОС; docs3/3.
- [ ] Следующий этап: ABI void/double/hard-float, стековые аргументы, структуры и C++; затем RTOS по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API и прошивка прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R15

- Ветка `codex/rc3-api-r1`, после `77b6c4e`; перенос в ядро только после утверждения владельца.
- [x] O2/Os:32/32 F411/HLA GDB14/16; обычная отдельная прошивка без hooks, inline-кадры, две locations и потеря input после умножения.
- [x] Single-location адаптер отклоняет неоднозначность; прежний Og ELF сохранился. Начальный отказ линковки startup сохранён, оптимизация циклов startup ограничена отдельно.
- [x] Restore HW_BOOT/HW_GPIO PASS в обеих матрицах. [RU](docs/research/rc3-gdb-python/ru/r15.md) / [EN](docs/research/rc3-gdb-python/en/r15.md).
- [x] Windows/Linux58/58 host/prepare для каждой оптимизации на каждой ОС; docs3/3; format1/1 на канонической копии, исходный FAIL регистра Tests сохранён.
- [ ] Следующий этап: until/advance/nexti, строки и посторонние остановки; затем ABI по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R14

- Ветка `codex/rc3-api-r1`, после `f28ea37`; перенос в ядро только после утверждения владельца.
- [x] Последовательности перехватов:24/24 F411/HLA GDB14/16 на прежнем api_firmware; два отказа/успех, сохранение принятого результата, порядок и количество вызовов.
- [x] Намеренно неверное ожидание порядка отклонено; внутренний retry-алгоритм не проверялся. Restore HW_BOOT/HW_GPIO PASS, неожиданных FAIL/ERROR нет. [RU](docs/research/rc3-gdb-python/ru/r14.md) / [EN](docs/research/rc3-gdb-python/en/r14.md).
- [x] Windows/Linux56/56 host/prepare,25 host-тестов, docs3/3.
- [ ] Следующий этап: оптимизированный код O2/Os, inline, недоступные переменные и multiple locations; затем навигация по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API и исходники прошивок прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R13

- Ветка `codex/rc3-api-r1`, после `869f884`; перенос в ядро только после утверждения владельца.
- [x] WFI/SysTick/TIM2:16/16 F411/HLA GDB14/16 на прежнем CMSIS ELF; PC, стек, возврат и восстановление задержки проверены.
- [x] Restore HW_BOOT/HW_GPIO PASS, неожиданных FAIL/ERROR нет. [RU](docs/research/rc3-gdb-python/ru/r13.md) / [EN](docs/research/rc3-gdb-python/en/r13.md).
- [x] Windows/Linux53/53 host/prepare, Linux CMSIS prepare2/2, docs3/3. Энергия и длительность сна не измерялись.
- [ ] Следующий этап: последовательности перехватов — отказы, повторы, успех и порядок вызовов; затем оптимизированный код по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API и исходники прошивок прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R12

- Ветка `codex/rc3-api-r1`, после `2bd17d2`; перенос в ядро только после утверждения владельца.
- [x] DMA/write/access: 16/16 F411/native DAP GDB14/16, тот же CMSIS ELF. Буфер изменён до CPU-чтений без watch stop; CPU-контроли и приёмники PASS.
- [x] Restore HW_BOOT/HW_GPIO PASS, неожиданных FAIL/ERROR в R12 нет. [RU](docs/research/rc3-gdb-python/ru/r12.md) / [EN](docs/research/rc3-gdb-python/en/r12.md).
- [x] Windows/Linux51/51 host/prepare; R12 prepare на CMSIS ELF, Linux2/2.
- [ ] Следующий этап: WFI, сон и пробуждение; затем последовательности перехватов по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API и исходники прошивок прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R11

- Ветка `codex/rc3-api-r1`, после `7f06a5d`; перенос в ядро только после утверждения владельца.
- [x] SysTick/TIM2: 16/16 HW F411/HLA GDB14/16 на существующей CMSIS-прошивке; стек GDB и аппаратный кадр, locals, естественный return, restore PASS.
- [x] Сохранены исходный FAIL выбора delay2мс и ERROR чтения start; добавлены условие delay500мс и явный optimized_out.
- [x] Windows/Linux49/49 host/prepare, затронутые3/3; R11 prepare на CMSIS ELF, Linux2/2. [RU](docs/research/rc3-gdb-python/ru/r11.md) / [EN](docs/research/rc3-gdb-python/en/r11.md).
- [ ] Следующий этап: DMA и watchpoints, затем сон/пробуждение; продолжать по [очереди](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9).
- Ядро/API и исходники обеих прошивок прежние. Для R11 нужен CMSIS ELF, не api_firmware; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R10

- Ветка `codex/rc3-api-r1`, после `67066e2`; перенос в ядро только после утверждения владельца.
- [x] F411/HLA GDB14/16: 8 ожидаемых fault ERROR +8 timeout ERROR, 16/16 контролей PASS, restore HW_BOOT/HW_GPIO PASS.
- [x] Исходный ERROR неверного имени xpsr сохранён; исправлено на xPSR. Host отвергает посторонние ошибки и неполные доказательства.
- [x] Windows/Linux47/47 host/prepare, после исправления затронутые4/4; [RU](docs/research/rc3-gdb-python/ru/r10.md) / [EN](docs/research/rc3-gdb-python/en/r10.md).
- [ ] Следующий этап: IRQ, стек прерванного кода и возврат из исключения; затем DMA.
- Полная [очередь до итогового обсуждения](docs/research/rc3-gdb-python/ru/plan.md#очередь-продолжения-после-r9) сохраняется; после каждого этапа сообщать следующий.
- Ядро/API и прошивка прежние; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R9

- Ветка `codex/rc3-api-r1`, после `e9b389e`; перенос в ядро только после утверждения владельца.
- [x] Прерванные calls: resume и вложенный intercept16/16 F411/HLA GDB14/16, restore HW_BOOT/HW_GPIO PASS.
- [x] DUMMY_FRAME распознаётся по типу, а не имени; восстановление регистров не откатывает RAM, исходное Python-выражение не возобновляется.
- [x] Windows/Linux44/44 host/prepare; [протокол RU](docs/research/rc3-gdb-python/ru/r9.md) / [EN](docs/research/rc3-gdb-python/en/r9.md).
- [ ] Далее fault/timeout во время call и IRQ; затем RTOS и переносимость других плат/ABI. Ядро и прошивка прежние.
- Публичный API прежний; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R8

- Ветка `codex/rc3-api-r1`, после `40901eb`; перенос в ядро только после утверждения владельца.
- [x] FPB/finish: HLA16/16 GDB14/16, native DAP8/8 GDB16; шесть code-слотов с четырьмя guard, восстановление без reset.
- [x] Исходный ERROR обращения к недействительной FinishBreakpoint сохранён. Все firmware restore PASS.
- [x] Windows/Linux42/42 host/prepare; [протокол RU](docs/research/rc3-gdb-python/ru/r8.md) / [EN](docs/research/rc3-gdb-python/en/r8.md).
- [x] План, отчёты R1–R8 и результаты собраны в [папке исследования](docs/research/rc3-gdb-python/ru/index.md); правила структуры и CI обновлены.
- [ ] Далее IRQ/RTOS, прерванные calls и другие ABI/платы. Ядро и прошивка прежние.
- Публичный API прежний; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R7

- Ветка `codex/rc3-api-r1`, после `435639d`; перенос в ядро только после утверждения владельца.
- [x] WIDTH/CAPACITY16/16, SPLIT8/8; отказы не скрыты, исходные FAIL/ERROR сохранены. Все restore PASS.
- [x] Windows/Linux40/40 host/prepare; [протокол RU](docs/research/rc3-gdb-python/ru/r7.md) / [EN](docs/research/rc3-gdb-python/en/r7.md).
- [x] Тот же ELF R6, без новых hooks или правок ядра. Измерена граница4/5 word-точек на F411 native DAP.
- [ ] Далее FPB, IRQ/RTOS, прерванные calls и переносимость других ABI/плат.
- Публичный API прежний; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R6

- Ветка `codex/rc3-api-r1`, после `191244d`; перенос в ядро только после утверждения владельца.
- [x] Отбор по стеку и рекурсивные finish/return:24/24; первый FAIL предположения callback сохранён.
- [x] Windows/Linux37/37 host/prepare; [протокол RU](docs/research/rc3-gdb-python/ru/r6.md) / [EN](docs/research/rc3-gdb-python/en/r6.md).
- [x] Новый ELF/GDB16: положительная ABI-регрессия32/32, старый SRET отклоняет ELF до записи. Все restore PASS.
- [ ] Далее границы DWT/FPB, IRQ/RTOS, прерванные calls; полный прежний HW-набор не заявляется.
- Публичный API прежний; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R5

- Ветка `codex/rc3-api-r1`, после `2c6c8a6`; перенос в ядро только после утверждения владельца.
- [x] Матрица типов возврата:64/64; struct-return FAIL GDB14/16 сохранён; адресный SRET-прототип8/8.
- [x] Windows/Linux host/prepare34/34; [протокол RU](docs/research/rc3-gdb-python/ru/r5.md) / [EN](docs/research/rc3-gdb-python/en/r5.md).
- [x] Регрессия нового ELF/GDB16: R4 16/16 и R3 DEADLINE/SAMEVALUE 8/8; все restore PASS.
- [ ] Далее void/double/hard-float, рекурсия/IRQ, границы DWT и прерванные calls. Полная регрессия прежних серий на новом ELF не заявляется.
- Публичный API прежний; публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R4

- Ветка `codex/rc3-api-r1`, после `8ec9978`; перенос в ядро только после утверждения владельца.
- [x] Выходной буфер + signed-статус: natural/success/error/short, 32/32 F411 GDB14/16 native DAP; restore PASS.
- [x] Windows/Linux build/host/prepare 24/24, формат затронутого C PASS; [протокол RU](docs/research/rc3-gdb-python/ru/r4.md) / [EN](docs/research/rc3-gdb-python/en/r4.md).
- [x] Регрессия нового ELF/GDB16: R1 24 PASS, R2 7 PASS + ASM ERROR native DAP; ASM HLA 4 PASS, R3 16 PASS. Все restore PASS, исходный ERROR сохранён.
- [ ] Далее типы возврата, рекурсивные вызовы и границы DWT; ядро и публичный API прежние.
- Публикация/land — владелец.

## Предыдущая работа: consumer-эксперименты rc3 R3

- Продолжаем `codex/rc3-api-r1` после R2-коммита `33938d2`; перенос в ядро только после утверждения владельца.
- [x] Команды точек, progress deadline с переполнением, same-value watch/awatch, макросы и ветвления: 32/32 F411 GDB14/16 native DAP.
- [x] Restore HW_BOOT/HW_GPIO PASS; [протокол RU](docs/research/rc3-gdb-python/ru/r3.md) / [EN](docs/research/rc3-gdb-python/en/r3.md).
- [x] Windows/Linux build/host/prepare 20/20; 20 host-регрессий. Старый общий format FAIL остаётся.
- [ ] Границы DWT, рекурсия/IRQ, выходные буферы/ABI и interrupted calls; другие платы отдельно.
- Публикация/land — владелец. Публичный API, ТЗ и версия пакета прежние.

## Предыдущая работа: consumer-эксперименты rc3 R2

- Продолжаем в `codex/rc3-api-r1` после `0d0db6a`; зависимости веток прежние.
- **Перенос в ядро и изменение публичного API — только после явного утверждения владельца.**
- [x] Навигация, C-контекст, caller, условные/однократные точки, return/finish/call, ассемблер: 56/56 на F411 с GDB14/16, HLA.
- [x] WATCH FAIL на HLA сохранён для обеих версий; native DAP/SWD сравнение: 8/8, write/read/access events распознаются.
- [x] После каждой серии restore + HW_BOOT/HW_GPIO PASS; [протокол RU](docs/research/rc3-gdb-python/ru/r2.md) / [EN](docs/research/rc3-gdb-python/en/r2.md).
- [x] Windows/Linux build/host/prepare 16/16; 17 host-регрессий. Старый общий format FAIL не исправлялся.
- [ ] Same-value store, границы watchpoints, условия/рекурсия/IRQ, out-buffer/ABI и interrupted calls — следующие эксперименты, без переноса в ядро.

## Предыдущая работа: consumer-эксперименты rc3 R1

- Ветка `codex/rc3-api-r1` зависит от исследования `9fce519`; порядок принятия: исследование → R1.
- [x] Обычная прошивка F411 без hooks, шесть сценариев, двенадцать host-регрессий адаптера.
- [x] Windows/Linux build + host/prepare 8/8; формат новых C/H PASS, общий format FAIL на прежнем HAL-коде.
- [x] F411/ST-Link/OpenOCD: 48/48 на одном ELF с GDB14/16; 4 ожидаемых ERROR и положительные контроли; restore boot/GPIO PASS.
- [x] Исходный ERROR сохранён, [протокол RU](docs/research/rc3-gdb-python/ru/r1.md) / [EN](docs/research/rc3-gdb-python/en/r1.md).
- [ ] Оставшиеся границы E01–06/E20 и публичные контракты; перенос в ядро только с новой ревизией ТЗ и API/миграциями.
- Публикация/land — владелец. Это прототип, версия пакета и API не меняются.

## Предыдущая работа: исследование 0.1.0rc3

- Ветка `codex/rc3-gdb-python-research` от main `da42cd7`.
- [x] API, техники и сценарии сверены с кодом; руководство GDB Python и внешние модели изучены.
- [x] [План RU](docs/research/rc3-gdb-python/ru/plan.md) / [EN](docs/research/rc3-gdb-python/en/plan.md): P0/P1/P2, E01–E20, Nucleo-F030R8, BluePill-Plus, BlackPill F411CE/F401CC.
- [x] Read-only L0 probe GDB14/Python3.11 без ELF, сервера и MCU; наличие API не означает HW PASS.
- [x] L0 GDB16/Python3.13 из GCC15: дополнительные API и timeout-параметры присутствуют; сравнение с GDB14 сохранено.
- [ ] Выбрать первый пакет R1, согласовать стенд/restore; создать consumer fixture и выполнить опыты.
- [ ] Новые API после доказательства: регрессии, API/миграции RU/EN, CHANGELOG, новая ревизия ТЗ.
- Публикация ветки и land — владелец; пакет остаётся rc2, ТЗ0.58.

## Предыдущая группа HAL GPIO/RCC

- codex/f030-hal-gpio-rcc зависит от аудита4c51122: пять HAL-техник одной группой.
- [x] Windows24/24 prepare/host, Linux HAL24/24 + negative contracts; host обеих ОС.
- [x] Строгий выбор mutable/const RCC по двум reviewed SHA256; неизвестный source отклоняется.
- [x] Итоговый HW22 +15 повторов, timeout/recovery и автоматический restore; протокол F030_HAL_GPIO_RCC.md.
- [ ] Публикация GPIO/RCC, Docs и полный Offline, затем land после аудита.
- [x] Аудит4c51122: Docs36886450888, Offline36886505225 SUCCESS; ожидает land владельцем.
- [x] RTC/Sleep b8d66e0 принят в main.
- [ ] Порядок land: аудит → HAL GPIO/RCC; затем независимый F411-consumer.

## Предыдущий аудит

- Ветка codex/cmsis-migration-audit зависит от RTC/Sleep b8d66e0; только документация.
- [x] Сверить 105 HAL и 98 CMSIS board cases; см. docs/ru/CMSIS_ACCEPTANCE.md.
- [ ] Сохранить пять HAL GPIO/RCC cases одной группой: F030 fixture после review HAL либо отдельный F4 fixture; затем HW/recovery/restore.
- [ ] Опубликовать аудит, запустить Offline вручную (Markdown-фильтр), проверить Docs и полный Offline.
- [x] RTC/Sleep b8d66e0: опубликован, Docs36884302983 и Offline36884302932 SUCCESS.
- [x] ADC/DMA52c49fd принят в origin/main, SHA сверен.
- [ ] Land RTC/Sleep владельцем, затем аудит после собственного CI.

## Предыдущая группа RTC/Sleep

- codex/f429-cmsis-rtc-sleep зависит от codex/f429-cmsis-adc-dma52c49fd; порядок land: ADC/DMA → RTC/Sleep.
- [x] Windows prepare21/21, HW20/20 +5 повторов, host timeout/recovery и HAL boot/blink restore.
- [x] Windows docs/host 4/4 и Linux 17/17; RU/EN, ТЗ 0.57.
- [x] Docs36882263763 и полный Offline36882263685 ADC/DMA52c49fd PASS.
- [x] ADC/DMA принят владельцем, origin/main52c49fd сверен.
- [x] RTC/Sleep опубликован; Docs/полный Offline SUCCESS, fast-forward от52c49fd возможен.
- [ ] Land RTC/Sleep владельцем.
- [x] Итоговая сверка пяти профилей HAL→CMSIS: CMSIS_ACCEPTANCE.md; пять HAL GPIO/RCC cases ещё нужно сохранить.
- [ ] Перевести независимый F411-consumer и проверить интеграцию, затем сократить BlackPill до F411.
- [ ] Оптимизация тестов/CI после переноса; автоматические аппаратные метрики — отдельный этап.

## F429 ADC/DMA: принят в main52c49fd

- [x] HW15/15 +3 повтора, HAL restore; Windows prepare16/16, docs/host4/4, Linux17/17.
- [x] Ветка опубликована, SHA сверен; Docs SUCCESS.
- [x] Полный Offline (пять jobs) SUCCESS.
- [x] Land владельцем подтверждён, origin/main52c49fd сверен.

## F429 baseline: принят в main7a261e8

- [x] HW7/7 и HAL restore, Windows prepare8/8, Windows docs/host4/4, Linux17/17.
- [x] Docs36874758483 и полный Offline36874758494 PASS; land владельцем, origin/main сверен.

## F401 RTC/Sleep: принят в main9d22410

- [x] HW20/20 +5 повторов, host timeout/recovery и HAL restore; Windows prepare21/21.
- [x] Windows docs/host4/4, Linux14/14, ТЗ0.54; Docs36871974569 и полный Offline36871974507 PASS.
- [x] Land владельцем подтверждён, origin/main9d22410 сверен.

## F401 ADC/DMA: принят в main87a23be

- codex/f401-cmsis-adc-dma: ADC1/DMA2/factory units/failures.
- [x] Windows prepare16/16, HW15/15 +3 повтора, HAL boot/blink.
- [x] Windows docs/host4/4, Linux format/host +12 MCU/GCC сочетаний14/14.
- [x] Docs36869402038 и полный Offline36869402018 PASS; land владельцем подтверждён.

## F401 baseline: принят в mained5557f

- codex/f401-cmsis-baseline от main591c096: clocks/GPIO/SysTick/TIM2, группа из семи сценариев.
- [x] Windows build/prepare8/8, HW7/7, восстановление HAL boot/blink.
- [x] Windows docs/host4/4, Linux format/host + четыре MCU × три GCC:14/14 PASS.
- [x] Docs/Offline ed5557f прошли; land подтверждён.
- [x] Группы F401 ADC/DMA/units/failures и RTC/Sleep/recovery приняты; см. разделы выше.
  Старые HAL-профили сохраняются до итоговой сверки переноса.

## README-метрики: приняты в main591c096

- codex/hardware-metrics-readme от main `91a7cd4`: документальный срез CMSIS-метрик.
- [x] README RU/EN: бейджи, пояснение, таблица доказательств и правила подсчёта.
- [x] Docs и полный Offline591c096 прошли; land подтверждён.
- [ ] Автоматизировать отдельную полную HW-кампанию: manifest ожидаемой матрицы,
  агрегатор локальных/CI отчётов с SHA/ELF, отдельный статус последней попытки
  и последний успешный результат; публикация JSON в ci-badges после проверки.
  Пока бейджи статические, исторические; API и ТЗ0.51 не меняются.

## Предыдущая группа: принята в main 91a7cd4

- codex/f411-cmsis-rtc-sleep от main4a6f5d3: RTC/Sleep/deadlines/recovery одной группой.
- [x] F411/OpenOCD20/20 HW +5 повторов; host timeout/recovery, HAL boot/blink восстановлены.
- [x] Windows prepare/traceability21/21; протокол RU/EN и ТЗ0.51.
- [x] Windows docs/host4/4, формат PASS; Linux host/девять MCU/GCC10/10 PASS.
- [x] Группа опубликована, полный Docs/Offline прошёл, land выполнен.
- [x] Сверка и gitlink потребителя приняты в stm32-hwtest-blackpill `84a257e` после CI.
- [ ] Согласовать дальнейший перенос примеров и оформление BlackPill как F411-потребителя; старые профили пока не удалять.

## История F411 ADC/DMA (принята)

- main4a6f5d3: Docs36856728377 и Offline36856728367 (все пять jobs) SUCCESS; land подтверждён.
- 15/15 HW +3 повтора, HAL restore; Windows16/16, Linux10/10; ТЗ0.50.

## История F411 baseline (принята)

- main cb17bdf: Docs36854198027 и Offline36854197751 (все пять jobs) SUCCESS; land подтверждён.
- 7/7 HW, HAL restore, Windows prepare8/8, Linux10/10; ТЗ0.49.

## История группы F103 RTC/Sleep (принята)

- main d97903c: Docs36851177855 и Offline36851177857 (все пять jobs) SUCCESS; land подтверждён.
- 20/20 HW + пять повторов, host timeout/recovery, HAL restore; протокол хранит ACL-ошибки первого restore. ТЗ0.48.

## История группы F103 ADC/DMA (принята)

- main3e123ad: Docs36841424006 и Offline36841423947 (все пять jobs) SUCCESS; land подтверждён.
- 15/15 HW + три повтора; Windows prepare16/16, docs/host4/4, Linux host/firmware10/10; HAL восстановлен, ТЗ0.47.

## История группы F103 baseline (принята)


- codex/f103-cmsis-baseline от main a0d6547 (опубликован rc.2).
- [x] Группа clocks/GPIO/SysTick/TIM2: 7/7 HW, исходная HAL восстановлена.
- [x] Windows host/prepare, Linux host + девять MCU/GCC сочетаний PASS; ТЗ 0.46, RU/EN протокол.
- [x] main352417c: Docs36833032263 и Offline36833032031 (все пять jobs) SUCCESS; land подтверждён.
- [ ] Следующие группы: F103 ADC/DMA/арифметика/отказы; RTC/Sleep/deadlines/recovery;
  затем F411. Не создавать отдельный цикл GitHub для каждой периферии.

## История выпуска rc.2 (завершён)

Все условия ниже выполнены: тег a0d6547 Verified; потребитель main2b9d75f,
Offline SUCCESS. Незакрытые отметки в исходном плане ниже — история подготовки.


- codex/release-0.1.0-rc.2 от main eaf31ea: Python 0.1.0rc2, API_VERSION=1,
  ТЗ 0.45 к выпуску, итоговый текст docs/releases/v0.1.0-rc.2.md. Тег не создан.
- [x] Документальный аудит eaf31ea принят: Docs и все пять Offline jobs SUCCESS.
- [x] Orange Pi и три стенда подтверждены владельцем; doctor без FAIL/WARN.
- [x] Локально Windows docs/host 4/4; Linux 14 этапов + чистый HAL 1/1.
  Первый HAL ERROR из-за Windows cache сохранён; runtime не исправлялся.
- [x] На 873f1ac: Docs и полный Offline (все пять jobs) SUCCESS. Последующие коммиты проверять отдельно.
- [x] Матрица 5b7b466 выполнена: пакеты Linux и локальный Windows; ST server — с USB reconnect, ограничение в RC2_READINESS.
- [x] Потребитель fb2d186 / модуль 67b7431: Offline SUCCESS (120 CTest), F411/OpenOCD 22/22 + recovery.
- [x] Текст выпуска согласован с фактическими результатами и ограничением USB.
- [x] README RU/EN: происхождение, исторические видео, схемы запуска и ограничения GDB.
- [x] d2c4beb: Docs/Offline SUCCESS; следующий документальный SHA проверяется отдельно.
- [ ] Проверить Docs/Offline итогового SHA, затем обновить gitlink потребителя и его CI;
  согласовать land и публикацию подписанного тега владельцем.
- [ ] После rc.2 продолжить CMSIS-перенос остальных профилей. Оптимизация CI —
  после переноса; consumer-профили сейчас не удалять.

## История этапов

Записи ниже фиксируют состояние на момент этапа, включая тогдашние планы.
Текущий порядок работы приведён выше; старое «далее» не является открытой задачей.

- codex/f030-hal-validation от codex/f030-hal-ci (`cc2cf19`): 17/17 HW,
  шесть положительных повторов, ожидаемый timeout/recovery, ADC после recovery,
  возврат исходной HAL-прошивки потребителя PASS. ТЗ 0.40, протокол RU/EN.
  Fixture a3898ff и CI cc2cf19 опубликованы: Docs и Offline (все пять jobs) SUCCESS.
  Порядок land: fixture → CI → validation после проверки опубликованного SHA.
  Локально Windows и Linux Docker: docs/host 4/4 PASS на каждой ОС.
  Далее обновить gitlink потребителя; старый HAL-профиль пока сохранить.

- codex/f030-hal-fixture от main69cfb79: автономный tests/hal-f030, 17 сценариев,
  TECH-ссылки, provenance и offline19/19 Windows/Linux GCC13. ТЗ0.38.
  Windows docs/format/host5/5, Linux docs/host4/4; Linux format отсутствует в
  локальном образе. Далее зависимые ветки HAL CI и HW validation; старый consumer
  сохраняется. Коммиты плана/руководства уже включены в main69cfb79.

- `codex/testing-techniques-guide` от `codex/f030-hal-regression-plan` (`caeafe1`):
  каталог TECH-001…008 (RU/EN), ссылки в сценариях, сборочные предпосылки и
  пределы доказательства. Только документация/комментарии, ТЗ 0.37 без изменений.
  Развивать карточки по новым практическим опытам, не терять HAL-приёмы при CMSIS.
  Сначала land плана, затем руководства; fixture/CI/HW остаются следующими этапами.

- Предыдущая ветка `codex/f030-hal-regression-plan` от `cea01f9`: подготовлен
  [план HAL fixture](docs/ru/F030_HAL_REGRESSION.md), исходная база потребителя
  `0c8c966`, полный начальный набор 17 сценариев. Только документация;
  новые HW-проверки не выполнялись. Windows/Linux docs 3/3 PASS.
  Далее зависимые ветки fixture → CI →
  HW validation, публикация пакетом по готовности. HAL-профиль не удалять.
- Завершён пакет ADC_BUSY → RTC_DEADLINE → CMSIS acceptance → lowercase:
  все четыре SHA прошли Docs и Offline, включены в main `cea01f9`.
  Потребитель обновил gitlink/каталоги tests: `0c8c966`, пять профилей CI PASS,
  ветка включена в main. Итоговые имена: tests и remote.toml; API_VERSION=1.
  Прежние16 +2 новых HW-сценария выполнены на одном ELF, HAL восстановлен.

- `codex/f030-cmsis-rtc` от `f494ab1`: RTC Alarm A/LSI и два сценария;
  16/16 HW PASS на новом ELF, HAL восстановлен. [Протокол](docs/ru/F030_CMSIS_RTC.md).
  Далее отказные ветви и итоговая приёмка HAL→CMSIS для F030.
  API ядра без изменений; ТЗ 0.33. F030 CTest 17/17, Windows host 96
  (8 skips), Linux docs/host/9 firmware pairs 13/13 PASS; strict ТЗ и формат PASS.

- `codex/f030-cmsis-sleep` от `a84b742`: два новых Sleep/WFI сценария,
  2/2 HW PASS; прежние 12 не повторялись, ELF тот же. HAL восстановлен.
  Проверки: F030 CTest 15/15, Windows host 96 (8 skips), Linux docs/host/
  9 пар firmware 13/13 PASS; strict ТЗ PASS.
  [Протокол](docs/ru/F030_CMSIS_SLEEP.md). Далее RTC и оставшиеся отказы.


- `codex/f030-cmsis-adc-units` от `a6c0426`: преобразование F030 ADC и
  7 численных/14 невалидных наборов; 12/12 HW PASS, HAL восстановлен.
  Проверки: F030 CTest 13/13, Windows host 96 (8 skips), Linux docs/host/
  9 пар firmware 13/13 PASS; strict ТЗ и формат PASS.
  [Протокол](docs/ru/F030_CMSIS_ADC_UNITS.md). Далее RTC/Sleep и отказы.


- `codex/f030-cmsis-adc-dma` от `5883316`: ADC/DMA raw и timeout F030,
  9/9 HW PASS, HAL восстановлен. [Протокол](docs/ru/F030_CMSIS_ADC_DMA.md).
  Проверки: host Windows 96 (8 skips), F030 CTest 10/10; Linux три профиля
  × GCC13/14/15 подтверждены первоначальным и исправленным F030-прогонами.
  Далее преобразование в физические единицы и численные векторы, RTC/Sleep.


- `codex/f030-cmsis-timer` от `40fafac`: TIM3/IRQ добавлены в F030 fixture;
  6/6 HW PASS на Nucleo/ST-Link/OpenOCD; HAL восстановлен.
  Offline: Windows host 96 (8 skips), Linux docs/host/9 firmware pairs 13/13 PASS,
  F030 CTest 7/7; strict ТЗ и формат PASS.
  [Протокол](docs/ru/F030_CMSIS_TIMER.md). Далее ADC/DMA/арифметика, RTC, Sleep.


- `codex/f030-cmsis-baseline` от `4601888`: первый этап CMSIS F030,
  boot/clock/GPIO/blink — 4/4 HW PASS (ST-Link/OpenOCD), HAL восстановлен.
  Windows host: 96 тестов, 8 skips; Linux docs/host/firmware: 13/13 PASS,
  F030/F103/F411 × GCC13/14/15; strict ТЗ: 0 ошибок/предупреждений.
  [Протокол](docs/ru/F030_CMSIS_BASELINE.md). Следующий этап — таймер/IRQ,
  далее ADC/DMA/RTC. Оптимизация CI остаётся после переноса примеров.


- `codex/cmsis-migration-inventory` от `bc07625` — [миграция примеров](docs/ru/CMSIS_MIGRATION.md)
  ([English](docs/en/CMSIS_MIGRATION.md)): сопоставлены 17 HAL-сценариев F030
  с двумя CMSIS-сценариями. Build/offline 3/3 PASS, без HW. Далее F030
  boot/clock/GPIO/blink, затем периферия и другие профили. Оптимизация CI — после переноса.
  Также переименован корневой Tests → tests; вложенные каталоги потребителей
  сохраняют совместимость. Gitlink потребителя менять после публикации и CI модуля.
  Проверки: Windows host 96 (8 skips); архив Git index извлечён в Linux filesystem,
  docs/host/firmware GCC13 для F030/F103/F411 — 7/7 PASS. ТЗ strict: 0 ошибок,
  0 предупреждений. Новый HW-прогон не выполнялся.

- `claude/tech-spec-0.1` — ТЗ ревизии 0.1 и правила коммитов; слита в main (PR #2).
- `claude/maintenance-rules` — AGENTS.md в виде краткого перечня, docs/ru|en/maintenance.md,
  ТЗ ревизии 0.2; слита в main.
- `claude/offline-ci` — подготовка к 0.1.0: `run --prepare-only`, offline-часть на Linux,
  CI-прошивки F030R8/F103C8/F411CE, Docker-образ, workflows Docs и Offline, ТЗ 0.3;
  проверено локально в Docker-образе (13/13: docs, host, 9 пар firmware); слита в main.
- `claude/hw-validation` — аппаратная проверка CI-прошивок до v0.1.0 (`tests/firmware/run_hw.py`:
  F411CE/ST-Link, F103C8/J-Link, F030R8/J-Link STLink), `.clang-format` и уровень format в CI,
  LED BluePill-Plus на PB2, выравнивание `.data`; 4 стенда × 10/10 шагов на `fbc103d`,
  ТЗ 0.4, STATUS; слита в main.
- `claude/bin-load-sections` — BIN только из выбранных секций (вопрос 11.2.17), ТЗ 0.5.
- `claude/docs-ru-en` (от `claude/bin-load-sections`) — сверка документации с кодом,
  перенос в `docs/ru` с переводами в `docs/en`, README.en.md, ТЗ 0.6. Далее: выпуск
  v0.1.0-rc.1 с повторной аппаратной проверкой на итоговом коммите.
- `claude/linux-stand` — все сценарии размещения стенда до v0.1.0, группы A и B:
  аппаратный запуск на Linux (`flock`, группы процессов), окружение Ubuntu 20.04 без
  root `tools/linux_stand.py`, `doctor`, CI `linux-stand`, ТЗ 0.7; слита в main.
- `claude/remote-server` — группа C (удалённый GDB-сервер по SSH, ТЗ 0.9), `doctor` ищет
  GDB как `run_hw.py`, определение проекта как реализации DDTT, спецификация DDTT 0.1,
  сверка документации с кодом (ТЗ 0.10).

## Сценарии размещения стенда до v0.1.0

- [x] Windows локально (проверено на 4 стендах).
- [x] Orange Pi 5 (Ubuntu 20.04 aarch64) локально — 3 стенда × 10/10.
- [x] WSL2 (Ubuntu 20.04 x86_64) → сервер на Orange Pi 5 по SSH — 3 стенда × 10/10 (ТЗ 0.15, TC-112).
- [ ] Технический долг: WSL2 + usbipd-win (у владельца конфликт с фильтрами USB USBPcap
  и nxusbf) и отдельный Linux-ПК x86_64 с отладчиком — реализовано, на оборудовании не проверялось.
- [x] Группа C: runner и GDB на Windows или в WSL, GDB-сервер и отладчик на Orange Pi 5
  по SSH (туннель, удалённая блокировка, таблица `[remote]`, только ключи) — реализовано
  (`claude/remote-server`, ТЗ 0.9), проверено с Windows: 3 стенда × 10/10; обрыв связи
  (сигнал присутствия, ТЗ 0.13) проверен выдёргиванием кабеля Orange Pi.
- [x] Группа D: сборка в одном месте, запуск на Orange Pi 5 (`pack`, `run --package`);
  аппаратный CI на self-hosted runner aarch64 (workflow Hardware, вопрос 11.2.16 ТЗ);
  прогоны в цикле (`run_hw.py --repeat`) — реализовано (`claude/prepared-runs`, ТЗ 0.12);
  проверено на Orange Pi 5: пакеты и цикл; workflow Hardware на раннере-службе — 3 стенда × 10/10.

## Этапы

- [x] Выделить ядро, API прототипа, самостоятельный пример и host fixtures.
- [x] Создать отдельную Git-историю и проверить подключение закреплённым подмодулем.
- [x] CI до GDB-сервера: host-тесты Windows/Linux, CI-прошивки на GCC 13/14/15, `prepare`.
- [x] Проверить новое подключение: проект потребителя на STM32G474 (Arduino Core STM32,
  stm32-cmake-yml, Windows → Orange Pi 5) — сценарий загрузки PASS; найден и исправлен отказ
  manifest без пакетов STM32Cube.
- [x] Выпущен v0.1.0-rc.1: версия `0.1.0rc1`, CHANGELOG, ТЗ 0.21 (`2143665`); итоговая проверка
  пройдена (CI, 4 + 3 стенда, workflow Hardware, G474 потребителя 4/4); README уточнён — тег опубликован владельцем.
- [ ] После rc.2 и устранения блокирующих замечаний — v0.1.0.
- [x] Перенести страницы `docs/*.md` в `docs/ru/` и добавить английские версии, README.en.md.
- [ ] Описывать совместимость по MCU/HAL/GDB/backend, а не по количеству тестов.
- [ ] Надзор за дочерними процессами при аварии host (Job Object и др.).
- [ ] Независимость от системы сборки (вопрос 11.2.23 ТЗ): стабильная схема `session.json` и команда
  её создания с явными параметрами; необязательный build manifest; к рассмотрению до v0.1.0.
  Позже — manifest из `compile_commands.json` без Ninja.
- [ ] Упаковка Python и console entry point как дополнительный способ поставки.
- [ ] Устранить обязательные OpenOCD-поля target schema и расширить переносимость build manifest.
- [ ] Документировать расширение профилей; не обещать поддержку непроверенного MCU.

## Внешнее согласованное управление стендом — отложено

- [ ] Контроллер в обычном host Python: источники питания, реле, имитаторы кнопок,
  измерительные приборы; драйверы оборудования остаются в проекте стенда.
- [ ] Команды/подтверждения и синхронизация с GDB-агентом, таймауты и журнал действий.
- [ ] Владение внешними ресурсами, безопасное завершение после ошибки/отмены.
- [ ] Сценарий power-cycle: ожидаемая потеря SWD/RSP, reconnect, повторная identity/Flash проверка.
- [ ] Разделять наблюдение работающего MCU и действия при halt; GDB API только в
  основном потоке GDB, без вызовов из фоновых потоков.

Этот интерфейс пока не реализуется; он учитывается как будущая граница ядра.

- [x] Перенести в модуль каноническую документацию API/contracts/macros/manifest/backend/identity/locks.
- [ ] При каждом изменении механизма обновлять его документацию здесь; результаты стендовых проверок — в проекте потребителя.

- [x] Оформить README как пользовательское введение и вынести подробное текущее состояние в docs/ru/STATUS.md.

## Образы и переносимость

- [x] Проверять Flash по ELF load sections/LMA, пропуская незагружаемые промежутки.
- [x] Явный BIN gap-fill 0xFF, границы/перекрытия до сервера, отрицательные host-тесты.
- [x] Полный образ с явным диапазоном/fill: BIN → односекционный ELF, readback
  gaps/tail, CRC-32/ISO-HDLC на ПК, единый payload debug/programming; без CRC-поля.
- [ ] CRC-поле/исключения и другие алгоритмы, сверка с MCU CRC, отдельный offline
  export/prepare CLI (полный режим через ST GDB Server уже проверен).
- [ ] Разделить адаптеры toolchain, MCU memory/identity и архитектурную диагностику;
  текущая доработка не объявляет production-поддержку RISC-V.

- [x] Проверить профиль Cortex-M0 через J-Link STLink: F030R8, существующие API/schema, host65 и 17 HW-сценариев потребителя.

- [x] rc.2: полный CMSIS F030 18/18 через SSH на a48158c; HAL restore PASS. Исправлены xPSR и RTC macro context; исходные ERROR сохранены в RC2_READINESS.

- [x] rc.2: HAL F030 через SSH на a48158c — 17/17, шесть повторов, timeout/recovery/restore PASS.
- [ ] После публикации исправленной выпускной ветки сверить новый SHA и полный CI; продолжить оставшуюся матрицу, не выполнять land заранее.

- [x] На 873f1ac: SSH lifecycle F030/OpenOCD, F103/J-Link, F411/OpenOCD — по 10/10, исходные HAL восстановлены.
- [ ] Перед Hardware workflow исправить F030 stand на Orange Pi (устаревший J-Link → родной ST-Link/OpenOCD); локальные SSH-проверки использовали правильный stand.

- [x] Исправление F030 stand на Orange Pi подтверждено; Hardware 36787681339 прошёл на 759840a, HAL восстановлены.
- [x] Повтор Offline/Hardware на 5b7b466: все 27 JSON из summary сохранены и сверены с GitHub. TC-133, ТЗ 0.44.

- [x] 5b7b466: Hardware 36788964902, по 10/10; 27 JSON GitHub сверены побайтно.
- [x] Windows F030 CMSIS 18/18, HAL 17/17 + повторы/recovery; F030/F103/F411 OpenOCD/J-Link lifecycle 10/10.
- [x] ST server F411: оставшиеся timeout/recovery проверены после USB reconnect; сохранить ограничение, не объявлять непрерывный 10/10. Все исходные HAL running.
- [ ] Подключить кандидата в основной репозиторий и выполнить интеграционную приёмку до финализации rc.2.
