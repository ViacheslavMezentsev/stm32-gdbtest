# rc3: исследование расширения Target API

[Документация](index.md) · [English](../en/plan.md)

[R2: навигация, вызовы и watchpoints](r2.md): 56/56 HLA и 8/8 native DAP; перенос в ядро только после утверждения владельца.

Дата: 02.10.2026. База: `da42cd74c27a01c21df47cd660e2533e9bcfc6d4`,
ветка `codex/rc3-gdb-python-research`. Цель — выбрать расширения для **0.1.0rc3**.
Это обзор и план экспериментов, **не реализованный API и не аппаратная приёмка**.
Имена предлагаемых методов предварительные. Версия Python пока `0.1.0rc2`,
`API_VERSION=1`, ТЗ 0.58; нормативные требования и схемы этим документом не меняются.

## Вывод и рекомендуемый состав

Нужны не все команды GDB, а композиция операций: **наблюдать → остановить по условию →
изменить вход/результат → продолжить → проверить последствия → восстановить**.
Самое полезное расширение rc3 — типизированные данные и память, структурированная
причина остановки, управление областью жизни точек/кадров и публичная запись
доказательств. Затем — hardware watchpoints и сценарии перехвата вызовов.
Вызов произвольной функции MCU, асинхронность и RTOS заслуживают отдельных опытов;
их не следует делать обязательным условием первого полезного набора rc3.

Рекомендация по приоритетам:

- **P0:** `record`, снимки значений/кадров, ограниченное чтение RAM,
  `run_until` с проверяемой причиной остановки, владение ресурсами и capabilities.
- **P1:** пошаговое выполнение и завершение вызова после проверки механизма точек,
  hardware watchpoints, журнал вызовов, аргументы/выходные буферы и последовательности
  подмен возврата; параметры и независимые оракулы.
- **P2:** прямые вызовы функций, C++/float ABI, запуск на интервал с остановкой,
  RTOS; каждый может остаться экспериментальным после rc3.
- **Вне первого rc3:** reverse execution на реальном STM32, универсальная трасса
  всех записей DMA, управление питанием/приборами, произвольная подмена PC,
  обобщённый allocator на MCU и нестандартный unwinder.

## 1. Что изучено в проекте

| Источник | Роль |
| --- | --- |
| [API](../../../ru/API.md), [Target](../../../../stm32_gdbtest/target.py), [agent](../../../../stm32_gdbtest/agent.py) | Публичные операции, выполнение, результаты и teardown |
| [Написание тестов](../../../ru/TEST_AUTHORING.md), [TECH-001…009](../../../ru/TESTING_TECHNIQUES.md) | Контекст, IRQ, инъекции, векторы и Sleep |
| [Контракты](../../../ru/CONTRACTS.md), [макросы](../../../ru/HAL_MACRO_GUIDE.md), [совместимость](../../../../stm32_gdbtest/compatibility.py) | ELF/preflight, source review и текущие проверки наличия API |
| [CMSIS-сверка](../../../ru/CMSIS_ACCEPTANCE.md), [HAL GPIO/RCC](../../../ru/F030_HAL_GPIO_RCC.md) | Что сохранено при миграции; границы аппаратных доказательств |
| [Проверки](../../../ru/testing.md), [приёмка rc2](../../../ru/RC2_READINESS.md) | Offline/HW, recovery, восстановление и сохранение ошибок |

AST-инвентаризация текущей базы: **24 файла с 121 декоратором `@case`**:
98 CMSIS (F030:18, F103/F401/F411/F429: по20), 22 HAL F030 и один minimal-consumer.
ID повторяются между профилями: это число сочетаний «профиль + сценарий», не
число глобально уникальных ID и не процент покрытия. Изучены реализации групп
boot/GPIO/clock, ADC/DMA, численных векторов, RTC/deadline, Sleep и HAL-инъекций.

| Существующая техника и пример | Что уже возможно | Пробел API |
| --- | --- | --- |
| TECH-001/002, [RTC F103](../../../../tests/firmware/profiles/f103c8/tests/board/test_rtc.py) | Сохранить адрес/маску до смены macro context | Нет типизированного снимка и явного объекта контекста |
| TECH-003, [HAL runtime](../../../../tests/hal-f030/hal_scenarios/peripheral_runtime.py) | Дождаться callback/IRQ, сверить handle и публикацию | Нет общих ожиданий порядка/числа событий |
| TECH-004/005/009, [GPIO/RCC](../../../../tests/hal-f030/profile/tests/board/test_hal_methods.py) | Условный `reach`, NULL аргумент, принудительный return | Нет управляемой серии перехватов, capture аргументов и out-buffer |
| TECH-006, [ADC F411](../../../../tests/firmware/profiles/f411ce/tests/board/test_adc.py) | MMIO-инъекция, guard и timeout | Нельзя обобщать `set_value` на W1C/WO/read-to-clear: его before/after сами читают MMIO |
| TECH-007, [F030 vectors](../../../../tests/firmware/profiles/f030r8/tests/board/test_ci.py) | Подмена аргументов естественного вызова, независимые векторы | `value` всегда делает `int`; нет массива, строки, float и снимка структуры |
| TECH-008, [Sleep F411](../../../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py) | Прямые `gdb.Frame.older/type/pc`, проверка WFI | Нет публичного backtrace/disassembly; сценарии пишут во внутренний `report` |

`check` уже принимает Python-объекты, сравнимые через `==`; ограничение скалярами
находится главным образом в `value/fields`, а не в самом сравнении. JSON-совместимость
результата остаётся обязанностью вызывающего кода. `value` — общий GDB evaluator:
выражение может выполнить функцию или запись; название не гарантирует чистое чтение.
`breakpoint` возвращает живой объект GDB, а `reach` проверяет имя функции: передача
`file:line` или `*address` не даёт общего корректного `reach` без нового контракта.
`clear` удаляет и fault-handler breakpoints. Бюджет считает валидные объекты Target,
не все фактически занятые аппаратные locations, чужие и внутренние точки.

## 2. Руководство GDB: версия и карта чтения

Источник владельца: [gdb.pdf](../../../en/gdb.pdf), оставлен в исходном месте без изменений.
Титул: **GDB 19.0.50.20260922-git**, 1006 PDF-страниц.
SHA-256: `4f1dc20f2053dfe96a9db5e2f4f34a4398f67b72072609a01f468f031219d4b2`.
Это development manual, а не обещание наличия методов в поставляемом toolchain.
Ниже указаны физические PDF-страницы (нумерация просмотрщика, с1); в этой части
печатная страница меньше на18. Изучена Python-часть главы23 и связанные разделы.

| Раздел | PDF / печатные страницы | Применение |
| --- | --- | --- |
| Extending GDB; Python | 417; 427–556 / 399; 409–538 | Модель расширения и границы |
| Basic Python, Threading, Exceptions (§23.3.2.1–3) | 430–437 / 412–419 | execute, параметры, исключения, главный поток |
| Values, Types (§23.3.2.4–5) | 437–450 / 419–432 | Типы, поля, массивы, строки, lazy values, assign |
| Pretty-printers, frame filters, unwinders, xmethods | 450–475 / 432–457 | Диагностика и расширения контекста, не оракул корректности |
| Inferiors, Events, Threads (§23.3.2.17–19) | 475–487 / 457–469 | Память, остановки, выбор thread |
| Recordings; CLI/MI; Parameters | 487–503 / 469–485 | Ограничения backend, пользовательские команды и параметры |
| Frames, Blocks, Symbols, line tables (§23.3.2.28–32) | 510–522 / 492–504 | Аргументы, область видимости, PC, DWARF и исходные позиции |
| Breakpoints, FinishBreakpoints (§23.3.2.33–34) | 522–528 / 504–510 | Условия, ресурсы, завершение и return value |
| Architecture, registers, connections, disassembly | 532–546 / 514–528 | Структурированные регистры/инструкции; отдельные расширения UI |
| Auto-loading | 552 / 534 | Сохранить явную загрузку агента и выключенный auto-load |
| Watchpoints; Continuing/Stepping; Returning/Calling | 86; 103; 302–306 / 68; 85; 284–288 | Семантика наблюдения, шагов и inferior calls |

### Ограничения, которые меняют проектирование

1. **`Breakpoint.stop()` не место для инъекций.** В PDF с524 запрещается менять
   execution/frame/breakpoints и в общем случае данные. Обработчик выбирает остановку
   и сохраняет ограниченные наблюдения; `return`, запись и `continue` выполняются
   диспетчером в основном потоке после возврата управления из `gdb.execute`.
   Нельзя копировать произвольный callback-интерцептор стороннего фреймворка.
2. **Events — не аппаратная трасса.** `memory_changed/register_changed` сообщают
   об изменениях пользователем GDB, а не обо всех CPU/DMA-записях (PDF с481).
   При DMA память может меняться и при halt; последовательность чтений не атомарна.
3. **Finish не всегда hardware-only.** `FinishBreakpoint(frame, internal)` не
   принимает тип hardware; `finish/next/until` могут использовать внутренние точки.
   До доказательства их размещения нельзя обещать соответствие политике без Flash
   breakpoints. `return_value=None` означает void **либо** недоступный результат;
   inline не поддержан, `out_of_scope` не нормальный возврат (PDF с527–528).
4. **Вызов функции меняет MCU.** Это dummy frame, ABI, IRQ, стек и возможный hang;
   unwind не откатывает память/периферию. Таймауты вызовов в новом GDB зависят от
   async-target; внешний host timeout/recovery остаётся обязательным.
5. **Watchpoints ограничены целью.** `watch` ловит изменение значения, `awatch`
   может ловить доступ с тем же значением. Проверять width/alignment, ресурсы и
   фактическую вставку при resume; не разрешать незаметный software fallback.
   Наблюдение записи DMA проверяется отдельно, а не выводится из CPU-watchpoint.
6. **Живые объекты не являются снимками.** Frame/Value/Breakpoint могут стать
   недействительными после resume/reset; lazy value может читаться позже, чем ожидал
   автор. Сериализовать материализованные данные с ID остановки, не сохранять объект.
7. **Главный поток и таймауты.** `post_event` не гарантирует срок исполнения.
   Поток Python не должен вызывать `gdb.execute/parse_and_eval`. Даже описанный в новом
   руководстве thread-safe `interrupt` не отменяет действующего правила проекта:
   изменение модели потоков требует отдельного решения, а не скрытого обхода.

### Выполненный опыт без MCU

02.10.2026 запущен [probe](../../../../tools/research/gdb_api_probe.py) с `-nx -nh -batch`,
без ELF, сервера и target connection; [машиночитаемый результат](../results/rc3-gdb14-capabilities.json).
GDB **14.2.90.20240526-git**, встроенный Python **3.11.4**, xPack GCC13.3.1-1.1, Windows.

| Проверка | Результат |
| --- | --- |
| Frame/read_var/read_register/older, Inferior read/write/search_memory, disassemble | Атрибуты присутствуют; HW-семантика не проверена |
| Breakpoint.locations, FinishBreakpoint/return_value, events.stop/cont | Присутствуют; вставка точек и остановки не проверены |
| with_parameter, post_event, Thread, blocked_signals | Присутствуют |
| Value.bytes, Value.is_unavailable, gdb.interrupt | Отсутствуют |
| direct-call-timeout, indirect-call-timeout, unwind-on-timeout | Параметры отсутствуют |
| may-call-functions / non-stop | true / false в чистом GDB |
| `int(gdb.Value(3.5))` / `float(gdb.Value(3.5))` | 3 / 3.5; подтверждает потерю дробной части при текущем подходе |

Повторить на каждой версии toolchain, подставив путь к GDB-Python:

```text
<GDB> -nx -nh -batch -ex "set auto-load off" -ex "source tools/research/gdb_api_probe.py"
```

Probe выводит `RC3_PROBE=<JSON>` и ничего не подключает. Наличие атрибута — только
уровень L0. L1 — операции с ELF без цели; L2 — семантика на конкретном MCU/backend;
L3 — повторяемость, отказные ветви и восстановление. У каждой capability нужны
эти уровни и причина недоступности; нельзя объявить общую поддержку по версии GDB.

### Дополнительная проверка xPack GCC15

После уточнения владельца проверен установленный xPack GCC **15.2.1-1.1**:
GDB **16.3.90.20250906-git**, Python **3.13.12**.
[Результат L0](../results/rc3-gdb16-capabilities.json) получен тем же probe без MCU.
В сравнении с GDB14 присутствуют `Value.bytes`, `gdb.interrupt`, параметры
`direct-call-timeout`, `indirect-call-timeout`, `unwind-on-timeout`.
Значения параметров: `None` (unlimited), `30` и `false` соответственно.
`Value.is_unavailable` отсутствует и здесь. Это не GDB19 из руководства.

GDB16 — предпочтительный кандидат для E15–17, но наличие API не доказывает
async-target, работающий timeout или допустимость вызова из worker-потока.
Для сравнения сначала оставить тот же ELF и выбрать GDB явно в session (`--gdb` у CLI — только для пакета);
пересборка GCC15 — отдельная переменная эксперимента. Глобальный PATH и базовый
GCC13 не менять. `Value.bytes` также не следует считать универсальным чтением
сырых target bytes с произвольным endian.

Уточнение стенда: владелец подтвердил WeAct BluePill-Plus на J-Link CE; это
согласуется с локальным F103/J-Link TOML. Для F411CE локальные файлы задают
ST-Link/OpenOCD и альтернативный ST-LINK GDB Server. Второй ST-Link владелец
сопоставил с Nucleo-F030R8; добавлен локальный OpenOCD TOML.
Старый F030/J-Link TOML содержит отладчик, отсутствующий в текущем USB-списке.

## 3. Предлагаемая поверхность API

Все имена в таблице — **кандидаты**. Это не готовые инструкции для текущего Target.

| Семейство | Кандидаты | Контракт и новые степени свободы |
| --- | --- | --- |
| Доказательства | `record(name, data)`, `snapshot(paths)` | JSON-примитивы, тип/width, stop ID, ограничение размера; reserved keys защищены, `t.report` не нужен |
| Данные | `read(path)`, `read_array(path, count)`, `read_string(path, max_bytes)` | int/bool/float/enum/pointer/структура; глубина/длина обязательны, NULL и unavailable различимы, NaN/Inf кодируются явно |
| Память | `read_memory(address, size)`, `write_memory(address, data)` | Материализованные bytes, диапазон и endian из цели; запись сначала только в согласованную RAM; MMIO отдельно |
| Кадры | `frames()`, `frame(index)`, `read_local(name, frame)`, `registers(names)`, `disassemble(address, count)` | Снимок PC/SP/тип/frame/line/unwind reason; временный выбор контекста с возвратом, запрет stale handles |
| Остановки | `run_until(location, when=...)`, `resume_until(handles)` | `StopRecord`: expected/fault/signal/exit/unexpected; function/file:line/address разрешаются по-разному, неоднозначность явная |
| Ресурсы | `breakpoints.scope()`, управляемые handles | Удалять только свои точки; fault guards отдельны. Учёт actual locations, FPB и data-watchpoint budgets, отказ без fallback |
| Шаги/завершение | `step_instruction`, `step_source`, `next`, `finish` | Чёткая операция и причина stop; предел числа шагов и общий deadline, стратегия return breakpoint проверена |
| Изменения | `write(path, value)`, `override_return(value)`, `patch_ram(...)` | Проверка типов/ABI, before/after для RAM; журнал попытки сохраняется и при ошибке, автоматический rollback только где доказан |
| Данные во времени | `watch(path, access=...)`, `expect_sequence`, `capture_calls` | Watchpoint/call count/order/аргументы; bounded stop history, не real-time trace и не coverage |
| Поведение вызовов | `intercept(function, actions=..., count=...)` | Main-thread dispatcher: snapshot → аргумент/out-buffer/return → resume; рекурсия, исчерпание сценария и IRQ явно ограничены |
| Вызов/прогон | `call(function, args)`, позднее `run_for(...)` | Отдельное разрешённое действие, не скрытый eval; состояние/таймаут/IRQ/ABI и postcondition определены |
| Проверки | masked/range/approx/sequence predicates, vector IDs | Сравнивать сохранённые значения без повторного MMIO-read; fail-fast по умолчанию |

Рекомендуется оставить `value` совместимым, добавляя новые операции, а не менять
его возвращаемый тип. Для `read(path)` использовать ограниченный путь к символу,
полю/индексу, чтение через Symbol/Frame/Value; произвольное C-выражение — отдельный
expert escape hatch. `may-call-functions=off` блокирует вызовы, **не** присваивания
и побочные эффекты MMIO, поэтому не является доказательством чистоты выражения.
Существующий прямой `import gdb` доступен доверенным сценариям и не является sandbox:
обёртка может журналировать только операции, проходящие через неё.

`snapshot` фиксирует выбранные значения в одной остановке, но не обещает
согласованность с работающим DMA. `patch_ram` восстанавливает только свои байты,
не всю систему. Не делать generic `patch_mmio` с read-modify-write/rollback:
RW/W1C/rc_w0/WO/read-to-clear требуют описания конкретного регистра и восстановления.
Нынешняя schema1 профиля не содержит RAM ranges и watchpoint budgets; новые поля
нельзя молча добавлять: сначала экспериментальная конфигурация, затем решение о схеме.

Для первого dispatcher достаточно естественных вызовов приложения. Комбинация
`call` + intercept внутри dummy frame — отдельный эксперимент, не следствие успеха
обычного `reach`/`return`. Если callback падает, ошибка должна стать ERROR, даже
если GDB лишь напечатал исключение и продолжил работу.

## 4. Что даёт обзор существующих инструментов

Источники проверены 02.10.2026; заимствуются идеи, не код и не зависимости.
Ни один из просмотренных источников не задаёт доказанно полный набор для всех
GDB/MCU/backend. Практический критерий полноты — покрытие нужных действий и
отказов матрицей экспериментов, а не количество методов.

| Источник | Полезная модель | Отличие от stm32-gdbtest |
| --- | --- | --- |
| [DOTT.NG overview](https://tw-ghub.github.io/dott-ng_docu/index.html), [developer guide](https://tw-ghub.github.io/dott-ng_docu/DeveloperGuide.html) | Ближайший аналог: halt/intercept points, вызовы и блочная память | Host pytest + GDB/MI; документированы helper library/test hook и ограничения callback. Наш запрет hooks сохраняется |
| [gMock cookbook](https://google.github.io/googletest/gmock_cook_book.html), [actions](https://google.github.io/googletest/reference/actions.html) | Ожидаемые аргументы, число/порядок вызовов, последовательности действий и возвратов | Compile-time mocks не доказывают реализуемость перехвата на MCU |
| [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html), [parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) | Setup/teardown, scope, именованные векторы | Не заменять AST-сбор `@case` динамическим discovery без отдельной миграции |
| [Hypothesis stateful](https://hypothesis.readthedocs.io/en/latest/stateful.html) | Генерация последовательностей действий и проверка модели | Сначала детерминированный replay, reset и ограниченный бюджет; автоматический shrinking на плате пока не нужен |
| [Zephyr Ztest](https://docs.zephyrproject.org/latest/develop/test/ztest.html), [Twister](https://docs.zephyrproject.org/latest/develop/test/twister.html) | Разделение harness, матрицы build/board и результата | Тестовый код часто выполняется в target image; переносится организация, не архитектура |
| [CMock](https://github.com/ThrowTheSwitch/CMock) | Генерация C mocks/stubs | Требует иного построения тестового бинарника; не готовая замена debugger-driven подхода |

Для собственного API полезно объединить три модели: GDB для механики, gMock для
ожиданий взаимодействий, pytest для жизненного цикла. Model-based tests — следующий
слой поверх стабильных детерминированных операций, не первая задача rc3.

## 5. Стенды и экспериментальная прошивка

Владелец предложил **Nucleo-F030R8, WeAct BluePill-Plus v1.1, WeAct BlackPill
F411CE и F401CC** и разрешил создавать тестовые проекты на основе имеющихся.
Это перечень кандидатов; он не подтверждает текущее подключение и не разрешает
немедленную перезапись Flash. Перед первым HW согласовать debugger/backend/SWD,
точный MCU BluePill (C8/CB не выводить из имени платы), питание и restore ELF/session.
F429 в этом наборе нет; существующие примеры используются только как источник идей.

| Этап | Плата | Назначение и backend-кандидат |
| --- | --- | --- |
| A | BlackPill F411CE | Основной M4/FPU: RAM, frames, шаги, вызовы; ST-Link/OpenOCD после подтверждения |
| B | BluePill-Plus v1.1 | M3, другой debugger/backend: J-Link, если владелец подтверждает; точный MCU до configure |
| C | Nucleo-F030R8 | M0, малый бюджет точек, ожидаемо ограниченные data-watchpoints; ST-Link/OpenOCD после подтверждения |
| D | BlackPill F401CC | Повтор M4 на другом профиле/карте памяти; ST-Link/OpenOCD после подтверждения |
| E | F411CE + другой сервер | ST-LINK GDB Server на том же согласованном отладчике, последовательно; затем remote Linux при необходимости |

Не нужна одновременная работа всех плат. Начать с F411CE; F030 и M3 проверяют
границы переноса, F401 — регрессию. Число FPB/DWT и доступность rwatch/awatch
измеряются; ожидание отсутствия watchpoint на M0 не заменяет проверку ответа сервера.

Предлагаемый будущий проект `tests/api-experiments/`: самостоятельный CMake consumer,
CMSIS startup/profiles из `tests/firmware`, обычная маленькая программа с арифметикой,
структурами, обработкой буфера, вложенными вызовами и периодическим IRQ.
Все функции вызываются обычной логикой приложения и сохраняются в ELF естественно.
Нет test hooks, специальных команд из MCU в runner или подмен production-прошивки.
Оракулы в Python независимы: фиксированные векторы, заранее заданные входы и
проверяемые постусловия. Буфер принадлежит программе, с отдельной фазой отсутствия
доступа CPU/DMA; не использовать произвольную «свободную RAM» или malloc из GDB.

Профили сборки: сначала `-Og -g3 -fno-lto` compile+link; отдельно `-O0`, `-O2`, LTO
как матрица доступности, а не способ скрыть отказ. F4 float: фактические
`-mfpu/-mfloat-abi` в manifest, отдельные soft/hard варианты; structs/64-bit return
не считать эквивалентом int return. C++ обычные методы/перегрузки отдельно от inline,
RTTI и исключений. FreeRTOS — отдельная поздняя программа, если понадобится E18.

## 6. Матрица экспериментов

На момент обзора R0 **E01…E20 ещё не выполнялись на MCU**. Последующие результаты
подмножества R1 приведены в [аппаратном протоколе](r1.md). Сначала host/fake-GDB отрицательные ветви,
затем ELF/preflight, затем одна плата. Для каждой строки сохраняются expected и actual,
включая отказ и восстановление; общая процедура ниже применяется ко всем строкам.
E01 включает уже выполненный L0, но его L1/L2 ещё предстоит выполнить.

| ID / приоритет | Действие и объект | Независимый критерий и отрицательный опыт |
| --- | --- | --- |
| E01 / P0 | Capability probe на GDB из GCC13/14/15, ELF каждого профиля | Наличие методов отдельно от реальной операции; отсутствующая capability даёт явную причину без подключения/инъекции |
| E02 / P0 | Typed read int32/uint64/enum/float/struct/array/string в app frame | Граничные константы, 3.5, NaN/Inf, NUL/длина, signedness; NULL/optimized-out/missing symbol/неподдержанный тип не превращаются в0 |
| E03 / P0 | Снимок locals/args/backtrace, затем resume и повторное чтение | PC/function/type/stop ID согласованы; stale frame отвергнут, контекст после временного select восстановлен; shadowed local различён |
| E04 / P0 | Read/write 1/2/4/8-байтовых RAM участков и буфера | Побайтовый эталон, canary вне диапазона, endian; выход за разрешённый диапазон отклонён до доступа; ошибка записи сохраняет попытку и частичный результат |
| E05 / P0 | run_until по функции, file:line и адресу; два BP на одном PC | StopRecord содержит фактические номера/PC; ambiguity/missing symbol/ложное условие/ошибка condition не дают успех; внешний BP не удалён |
| E06 / P0 | Scoped BP, fault guards, исчерпание бюджета и исключение в scope | Все свои ресурсы освобождены на PASS/FAIL/ERROR; guards сохранены, превышение actual locations/ошибка при resume видны; после reset обычный boot проходит |
| E07 / P1 | stepi/step/next через обычный вызов, ветвление и IRQ | Сравнить PC/инструкции/кадры с ELF; unexpected IRQ/fault не выдать за нужный шаг; доказать отсутствие software/Flash точек, иначе метод не принят |
| E08 / P1 | finish естественного вызова: int, void, uint64, struct; отдельно float | Возврат и side effects равны естественному пути; inline/недоступный результат/out_of_scope явны; установить стратегию hardware return point, не считать LR универсальным |
| E09 / P1 | CPU write/read/access watchpoint на aligned RAM; same-value store | Проверить changed-value против access semantics, PC и данные; отсутствие hardware, ширина, scope и исчерпание — явный отказ без software fallback |
| E10 / P1 | DMA пишет RAM при установленном data watchpoint | Отдельно зафиксировать срабатывание/несрабатывание; sentinel IRQ/конечный breakpoint ограничивает опыт, финальный буфер подтверждает DMA. Отсутствие stop не означает отсутствие записи |
| E11 / P1 | Capture естественных GPIO/арифметических вызовов: аргументы, count, order | Заданный список вызовов и отфильтрованные аргументы; лишний/пропущенный/переставленный вызов даёт FAIL внутри ограниченного окна, а не бесконечное ожидание |
| E12 / P1 | Серия return/error/argument/out-buffer подмен при естественных вызовах | Независимое постусловие вызывающего кода; триггер на N-м вызове; exhausted action list, рекурсия/IRQ и callback exception явны. Мутации только после stop dispatcher |
| E13 / P1 | Scoped patch RAM и временные параметры GDB, exception в теле | Восстановление своих байтов/параметров на всех исходах; teardown error сохраняется вместе с исходной ошибкой. MMIO rollback не заявляется |
| E14 / P1 | IRQ/Sleep: frame walk + disassembly вместо встроенного кода TECH-008 | Правильный exception, WFI и возврат; лимит попыток, недоступный unwind ERROR; это не измерение энергии или времени |
| E15 / P2 | Прямой call чистой функции и функции с RAM out-buffer из thread mode | Результат совпадает с естественным вызовом на тех же данных; SP/register context и canaries проверены, общий RAM-state отдельно; ABI/тип без DWARF отклонить |
| E16 / P2 | Вызов прерван breakpoint/fault либо не завершается | Dummy frame и исходная причина сохранены; внешний timeout завершает GDB и запускает recovery, положительный boot после восстановления. Call+intercept — отдельный подопыт |
| E17 / P2 | Продолжить на ограниченный интервал, остановить; local/remote | Доказать, что остановка действительно произошла; сигнал/потеря связи/зависший dispatch не маскируются. На GDB14 нет interrupt: сначала отдельный дизайн, не вызов GDB из worker |
| E18 / P2 | RTOS: threads, выбор task, locals, breakpoint thread filter | Только если сервер реально экспортирует задачи; иначе unsupported. IRQ не считать thread, snapshot selection восстановить; bare-metal single thread ничего не доказывает о RTOS |
| E19 / P1 | Векторы/matchers: masked/range/approx/sequence; затем bounded model replay | Независимые fixed vectors и намеренно неверное ожидание дают верный FAIL; уникальные vector IDs, seed+список действий для replay; reset между последовательностями |
| E20 / P0 | Отчёт/таймаут/teardown с крупным snapshot и ошибкой сериализации | Размер ограничен, ошибка не теряет основной результат; reserved keys не перезаписаны, ожидаемый ERROR остаётся ERROR, повторный пакет не удаляет прежний отчёт |

Host/fake-GDB проверки здесь проверяют наш контракт, а не имитируют доказательство
работы SWD. Для E06/E09 и всех внутренних точек нужен журнал фактического размещения
у сервера/RSP, при необходимости readback Flash до/после; отсутствие изменения Flash
само по себе ещё не доказывает hardware-only механизм. Нельзя включать Flash
breakpoints ради успешного finish. При невозможности подтвердить механизм — кандидат
остаётся experimental/unsupported для этой комбинации.

### Общий протокол одного опыта

1. Зафиксировать experiment ID, commit модуля/fixture, профиль MCU, GCC/GDB/Python,
   backend/версию, build flags, ELF/manifest SHA256, запрошенные capabilities и
   допустимое вмешательство. Серийные номера и локальные пути остаются вне Git.
2. Build/collect/trace/prepare. Оракул и ожидаемый отказ задать до HW.
   Перед записью — согласованный стенд и исходный restore ELF/session.
3. Baseline boot и нормальный путь, затем один опыт. Deadline сценария ограничен
   внешним host timeout; max stops/bytes/depth задаются заранее. Между точками CPU
   выполняется свободно, поэтому wall time не является точным временем MCU.
4. Сохранить `result.json`, JUnit, GDB/server/recovery logs, фактический StopRecord,
   input/output, попытки мутаций, cleanup errors. `unsupported/not-run` — статус
   исследования, **не новый SKIP** в runtime PASS/FAIL/ERROR.
5. Удалить свои ресурсы, восстановить разрешённые RAM/параметры; reset_run и
   отдельный положительный контроль. При конце серии — исходная прошивка и boot/blink.
   Если восстановление не удалось, остановить серию и сохранить ERROR.
6. После первого анализа выполнить заранее заданные3 положительных повтора для
   утверждаемой комбинации. Не перезапускать молча ради PASS; первый отказ остаётся
   в протоколе. Для IRQ-сценариев дополнительные bounded attempts описываются отдельно.

## 7. Порядок работ и критерий включения в rc3

| Пакет | Содержание | Выход |
| --- | --- | --- |
| R0 — этот обзор | Руководство, код, внешние модели, L0 probe | План и список открытых решений; без MCU |
| R1 | Fixture, StopRecord/ownership/record, typed snapshots, RAM | E01–06/E20 на F411; отказные host-тесты, воспроизводимый протокол |
| R2 | Шаги/finish/watchpoints | E07–10 на M4/M3/M0; решения по hardware-only и бюджету |
| R3 | Capture/intercept/cleanup/vectors | E11–14/E19; перенос одного HAL и одного CMSIS сценария без `t.report` |
| R4 | Calls/async/RTOS | E15–18 отдельно; принять либо явно отложить, не блокируя R1–R3 |
| R5 | rc3 acceptance | Повтор утверждённого набора на итоговом SHA, offline CI, независимый consumer, recovery/restore |

Каждый пакет — новая `codex/<задача>` от принятой базы; цепочки веток только с
зафиксированным порядком. Push/land с публикацией и тег — владелец. Экспериментальные
helpers сначала в consumer fixture; в ядро переносится механизм после доказательства.
Публичное изменение требует новой ревизии ТЗ, host-регрессий отказов, обеих API/миграций,
CHANGELOG и решения по `API_VERSION`/схемам. Версию rc3 менять при оформлении выпуска,
не выдавать подготовку за уже доступный релиз.

Для приёмки каждой операции: определены вход/выход/ошибки/владение/ограничения,
нет скрытого обхода потоков или Flash policy, сохранены JSON и исходные отказы,
проверен нормальный путь после вмешательства. Есть таблица
`операция × MCU × GDB × backend × build mode → evidence/unsupported/not-run`.
Не требуется объявлять все клетки поддержанными; требуется честно определить
поддержанный набор и регрессию прежнего API.

Открытые решения перед реализацией: состав P0/P1; публичный формат снимков и
StopRecord; бюджет/схема RAM и watchpoints; допустимые вмешательства calls/IRQ;
разделение естественного intercept и dummy-call intercept; окончательный стенд
и restore-проект. Универсальные power-cycle, многоплатность и покрытие кода
остаются отдельными задачами.

## Очередь продолжения после R9

Согласованный порядок дальнейших опытов. После каждого этапа публикуется
локальный отчёт с ограничениями и названием следующего этапа. Итоговое обсуждение
проводится после прохождения очереди; перенос в ядро отдельно утверждает владелец.
Номера будущих серий назначаются по факту, поскольку этап может потребовать
нескольких серий. Проверки на плате не заменяются host PASS.

| Порядок | Этап | Состояние |
| --- | --- | --- |
| 1 | Fault и зависание внутри call, диагностика и recovery | [R10](r10.md): 16 ожидаемых ERROR, 16/16 контролей PASS; ограничения в отчёте |
| 2 | IRQ, стек прерванного кода и возврат из исключения | [R11](r11.md): SysTick/TIM2 16/16; basic MSP, ограничения в отчёте |
| 3 | DMA и границы наблюдения через watchpoints | Следующий |
| 4 | WFI, сон и пробуждение | Ожидает |
| 5 | Последовательности перехватов: отказы, повторы, успех, порядок вызовов | Ожидает |
| 6 | Оптимизированный код: O2/Os, inline, недоступные значения и несколько locations | Ожидает |
| 7 | Оставшаяся навигация: until/advance/nexti, строки и посторонние остановки | Ожидает |
| 8 | ABI: void/double/hard-float, стековые аргументы, структуры, затем C++ | Ожидает |
| 9 | RTOS: задачи, контекст, фильтры — отдельная обычная прошивка | Ожидает |
| 10 | Надёжность: общий адрес точек, чужие точки, ошибки предиката, scope, восстановление настроек, бюджет call, bounded replay | Ожидает |
| 11 | Выбранные техники на F030/F103, согласование актуальных подключений | Ожидает |
| 12 | Сводная матрица возможностей/отказов и обсуждение результатов | После опытов |

## Источники и воспроизводимость

Основной фиксированный источник — PDF выше; актуальная HTML-документация может
меняться: [Python API](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Python-API.html),
[breakpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Breakpoints-In-Python.html),
[finish](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Finish-Breakpoints-in-Python.html),
[watchpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html),
[calls](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Calling.html).
Остальные первичные источники приведены в разделе4. Внешние проекты не запускались
и не устанавливались. Печатные формулировки сведены к собственному плану, полного
переноса текста руководства в Markdown нет.

Ограничения исходного обзора R0 (последующие опыты — [R1](r1.md)): не доказана
аппаратная работа на GDB из GCC14/15 и Linux; L0 не проверяет ABI, DWT/FPB, гонки IRQ или recovery.
Старые TODO/STATUS/API содержат исторические формулировки, поэтому база сверялась
с кодом и профильными протоколами, а не только со сводными счётчиками.
