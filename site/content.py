"""Content of the GitHub Pages site: skill routes and the API 3 reference (RU/EN).

Prose is localized; code fragments are shared. Fragments follow the API reference cards in docs/*/api
and the technique catalogue; "avoid" fragments show refused or discouraged patterns, not working recipes.
"""

DEMO = 'https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/'
DEMO_SITE = 'https://viacheslavmezentsev.github.io/demo-stm32-skills/skills/'
REPO = 'https://github.com/ViacheslavMezentsev/stm32-gdbtest'

# Colour by action (shared style): offline — no board, live — board access, alt — emulator or setup,
# view — results and warnings. danger is reserved for Flash writes and is not used for skills.
SKILLS = {
    'spec': dict(name='embedded-tech-spec', kind='offline', url=DEMO_SITE + 'embedded-tech-spec/',
                 ru='требования и тест-кейсы', en='requirements and test cases'),
    'integrate': dict(name='integrate', kind='alt', url=REPO + '/blob/main/skills/stm32-gdbtest-integrate/SKILL.md',
                      ru='подмодуль, HIL, пресеты', en='submodule, HIL, presets'),
    'scenarios': dict(name='scenarios', kind='offline', url=REPO + '/blob/main/skills/stm32-gdbtest-scenarios/SKILL.md',
                      ru='сценарий и контракт ELF', en='scenario and ELF contract'),
    'run': dict(name='run', kind='live', url=REPO + '/blob/main/skills/stm32-gdbtest-run/SKILL.md',
                ru='прогон на стенде', en='run on the stand'),
    'results': dict(name='results', kind='view', url=REPO + '/blob/main/skills/stm32-gdbtest-results/SKILL.md',
                    ru='разбор свидетельств', en='evidence review'),
    'develop': dict(name='develop', kind='live', url=REPO + '/blob/main/skills/stm32-gdbtest-develop/SKILL.md',
                    ru='FAIL → исправление → регрессия', en='FAIL → fix → regression'),
    'stand-loop': dict(name='stand-loop', kind='live', url=REPO + '/blob/main/skills/stm32-gdbtest-stand-loop/SKILL.md',
                       ru='конечные циклы комплекта', en='finite bundle cycles'),
    'hse': dict(name='hse-qualify', kind='live', url=REPO + '/blob/main/skills/stm32-gdbtest-hse-qualify/SKILL.md',
                ru='частота кварца и допуск', en='crystal frequency and tolerance'),
    'coverage': dict(name='coverage', kind='view', url=REPO + '/blob/main/skills/stm32-gdbtest-coverage/SKILL.md',
                     ru='карта и переносимые отчёты', en='map and portable reports'),
    'renode': dict(name='renode', kind='alt', url=REPO + '/blob/main/skills/stm32-gdbtest-renode/SKILL.md',
                   ru='ELF/GDB в модели', en='ELF/GDB on a model'),
    'emulator': dict(name='stm32-renode-emulator', kind='alt', url=DEMO_SITE + 'stm32-renode-emulator/',
                     ru='Renode и QEMU без платы', en='Renode and QEMU without a board'),
    'la': dict(name='weact-logic-analyzer', kind='live', url=DEMO + 'weact-logic-analyzer',
               ru='выводы MCU снаружи', en='MCU pins from outside'),
    'diag': dict(name='stm32-diag-record', kind='live', url=DEMO_SITE + 'stm32-diag-record/',
                 ru='SWD без остановки ядра', en='SWD without halting'),
    'ros': dict(name='stm32-ros-alt-channel', kind='live', url=DEMO_SITE + 'stm32-ros-alt-channel/',
                ru='поток в ROS1', en='stream into ROS1'),
    'rtt': dict(name='stm32-rtt-console', kind='live', url=DEMO + 'stm32-rtt-console',
                ru='консоль RTT', en='RTT console'),
    'swo': dict(name='stm32-swo-trace', kind='live', url=DEMO + 'stm32-swo-trace',
                ru='трассировка SWO/ITM', en='SWO/ITM trace'),
}

LEGEND = {
    'ru': [('offline', 'без платы: требования, сценарии'), ('alt', 'настройка, эмулятор'),
           ('live', 'работа с платой'), ('view', 'разбор результатов')],
    'en': [('offline', 'no board: requirements, scenarios'), ('alt', 'setup, emulator'),
           ('live', 'board access'), ('view', 'result review')],
}

# Module skills: when to use and the expected result (skills/README "Choosing and combining skills").
CHOOSE = [
    ('integrate',
     'Для первого подключения или смены версии. Дайте CMake-проект и нужный тег; сначала проверьте конфигурацию и prepare, затем один аппаратный сценарий.',
     'Закреплённый gitlink, HIL-конфигурация, пресеты и воспроизводимая команда запуска.',
     'First integration or version upgrade. Supply the CMake project and desired tag; verify configuration and prepare before one hardware scenario.',
     'Pinned gitlink, HIL configuration, presets and a reproducible run command.'),
    ('scenarios',
     'Когда требование к прошивке уже известно. Укажите наблюдаемое поведение и допустимые воздействия; берите ожидания из требования, а не из текущего ответа платы.',
     'Сценарий и контракт ELF; logical-time для порогов/retry, counter-cost для разности и расходов. external-capture — отдельная host-модель, не @case.',
     'A firmware requirement is already defined. Specify observable behaviour and allowed interventions; derive expectations from the requirement, not the current board response.',
     'Scenario and ELF contract; logical-time for thresholds/retry, counter-cost for deltas/cost. external-capture is a separate host fixture, not @case.'),
    ('run',
     'Для конкретного прогона. Передайте session или пакет и стенд; начинайте с doctor и prepare. После изменения кода переходите к develop, а не повторяйте запуск без гипотезы.',
     'Результат команды и сценария, журналы, восстановление и объяснение FAIL/ERROR/SKIP.',
     'Execute a specific attempt. Supply a session or package and stand; start with doctor and prepare. Code changes belong in develop, not unexplained retries.',
     'Command and scenario outcomes, logs, recovery and an explanation of FAIL/ERROR/SKIP.'),
    ('results',
     'Когда артефакты уже есть. Дайте полный каталог попытки или кампании и соответствующие исходники; сначала проверяйте происхождение и целостность, затем трактуйте записи.',
     'Отдельные исходы сценария, захвата, анализа и очистки. neutral-workflows связывает три примера с критериями; UNKNOWN не ноль, PASS кампании не отменяет намеренные FAIL.',
     'Evidence already exists. Supply the complete attempt or campaign and matching sources; check provenance and integrity before interpreting records.',
     'Separate scenario, capture, analysis and cleanup outcomes. neutral-workflows links three examples to criteria; UNKNOWN is not zero and campaign PASS preserves intended FAILs.'),
    ('stand-loop',
     'Для повторения принятого неизменяемого комплекта. Задайте конечное число циклов, политику FAIL/SKIP и STOP; при изменении ELF или сценария пересоберите комплект.',
     'Раздельные попытки, сводка цикла и review.json для агента; исходный проект на стенде не обязателен.',
     'Repeat an accepted immutable bundle. Define finite cycles, FAIL/SKIP policy and STOP; rebuild the bundle when the ELF or scenario changes.',
     'Separate attempts, cycle summary and review.json handoff; application sources are not required on the stand.'),
    ('develop',
     'Для изменения прошивки с обратной связью от схемы. Дайте требование, исходники, описание стенда и бюджет итераций; фиксируйте план и исходный FAIL до исправления.',
     'Требование → исходный дефект → исправление → тот же сценарий и повтор. Не скрывать retry через reset и не подгонять временные опоры по желаемому результату.',
     'Change firmware with feedback from the circuit. Supply requirements, sources, stand description and an iteration budget; retain the plan and baseline FAIL before fixing.',
     'Requirement → baseline defect → fix → same scenario and repeat. Do not hide retries with reset or fit clock anchors to desired results.'),
    ('hse',
     'Дайте номинал, допуск, плату и разрешённые воздействия; обоснуйте точность часов до аппаратного измерения.',
     'Интервал частоты, IN_TOLERANCE/OUT_OF_TOLERANCE/UNKNOWN, отдельный исход восстановления и границы эпохи.',
     'Supply nominal frequency, tolerance, board and allowed operations; establish clock accuracy before hardware measurement.',
     'Frequency interval, IN_TOLERANCE/OUT_OF_TOLERANCE/UNKNOWN, separate recovery verdict and epoch scope.'),
]

# Witnesses of the target (TTDD = DDTT + other witnesses).
WITNESSES = [
    (('GDB и SWD с остановками (DDTT)', 'GDB and SWD with stops (DDTT)'),
     ('состояние в точке остановки: переменные, регистры, MMIO, возвраты; подмена данных и отказов',
      'state at a stop point: variables, registers, MMIO, returns; injected data and faults'),
     ('ядро стоит в точках останова', 'the core halts at breakpoints'), ['scenarios', 'run']),
    (('SWD без остановки ядра', 'SWD without halting the core'),
     ('значения переменных и регистров во времени, пока прошивка работает', 'variables and registers over time while the firmware runs'),
     ('только чтение памяти по шине', 'bus memory reads only'), ['diag', 'ros']),
    (('Собственный вывод прошивки', "The firmware's own output"),
     ('лог, телеметрия и события, которые прошивка публикует сама', 'log, telemetry and events published by the firmware itself'),
     ('нужен канал в прошивке', 'needs a channel in the firmware'), ['rtt', 'swo', 'ros']),
    (('Выводы MCU снаружи', 'MCU pins from outside'),
     ('реальное время: фронты, ШИМ, джиттер ISR, шины на проводе', 'real time: edges, PWM, ISR jitter, buses on the wire'),
     ('нет, пассивный щуп', 'none, a passive probe'), ['la']),
    (('Модель без платы', 'A model without a board'),
     ('ход ELF на модели, обращения к периферии', 'ELF execution on a model, peripheral accesses'),
     ('нет; подготовка, а не проверка на цели', 'none; preparation, not a test on target'), ['renode', 'emulator']),
    (('Требования', 'Requirements'),
     ('что проверять: ID требований и тест-кейсов, допуски', 'what to check: requirement and test case IDs, tolerances'),
     ('—', '—'), ['spec']),
]

RULES = {
    'ru': [('Судит требование', 'Ожидание берётся из требования; каждый свидетель только подтверждает или опровергает его. Расхождение свидетелей — находка.'),
           ('Остановки меняют время', 'Время, частоты и джиттер измеряйте свидетелем, который не останавливает ядро; DDTT — конфигурация, ветвления, отказы.'),
           ('Один хозяин SWD', 'Не запускайте два GDB-сервера на один отладчик; анализатор и UART можно вести параллельно.'),
           ('Свидетельства рядом', 'Записи одного опыта связываются по ID сценария или требования и лежат рядом с result.json.'),
           ('Эмулятор — подготовка', 'Модель сокращает попытки на плате, но вывод «проверено на цели» даёт только плата.')],
    'en': [('The requirement judges', 'The expectation comes from the requirement; each witness only confirms or refutes it. Disagreeing witnesses are a finding.'),
           ('Stops change timing', 'Measure time, frequency and jitter with a witness that leaves the core running; keep DDTT for configuration, branches and faults.'),
           ('One SWD owner', 'Never start two GDB servers on one probe; an analyzer and UART may run in parallel.'),
           ('Evidence together', 'Records of one experiment share the scenario or requirement ID and sit next to result.json.'),
           ('An emulator prepares', 'A model saves board attempts, but only the board supports "verified on target".')],
}

ROUTES = [
    dict(id='new-project', nodes=['spec', 'integrate', 'scenarios', 'run', 'results'],
         ru=('Новый проект', 'Требования и тест-кейсы → подключение модуля → сценарии → прогон → разбор.'),
         en=('New project', 'Requirements and test cases → module integration → scenarios → run → review.')),
    dict(id='firmware-change', nodes=['scenarios', 'run', 'develop', 'run', 'results'],
         ru=('Доработка прошивки', 'develop на каждом шаге использует scenarios, run и results: исходный FAIL фиксируется до исправления, после — регрессия.'),
         en=('Firmware change', 'develop uses scenarios, run and results at each step: the baseline FAIL is recorded before the fix, the regression after it.')),
    dict(id='timing', nodes=['scenarios', 'run', 'la', 'results'],
         ru=('Временно́е требование', 'Настройку периферии проверяют MMIO и SVD, анализатор измеряет вывод без остановки ядра, results сводит оба свидетельства. Частота кварца — отдельный маршрут hse-qualify.'),
         en=('Timing requirement', 'MMIO and SVD check the peripheral setup, the analyzer measures the pin without halting the core, results relates both witnesses. Crystal frequency is the separate hse-qualify route.')),
    dict(id='operation', nodes=['scenarios', 'run', 'diag', 'results'], alt=['ros'],
         ru=('Поведение в работе', 'Сценарий DDTT подводит плату к состоянию и проверяет переходы, запись по SWD или в ROS1 пишет поток; запись лежит рядом с result.json под тем же ID.'),
         en=('Behaviour in operation', 'A DDTT scenario brings the board to a state and checks transitions, an SWD or ROS1 recording keeps the stream next to result.json under the same ID.')),
    dict(id='model-to-board', nodes=['renode', 'scenarios', 'run'], alt=['emulator'],
         ru=('Без платы → на плату', 'Короткий опыт и границы модели в Renode или QEMU, затем тот же сценарий на стенде.'),
         en=('No board → board', 'A short experiment and the model limits in Renode or QEMU, then the same scenario on the stand.')),
    dict(id='diagnostics', nodes=['run', 'rtt', 'results'], alt=['swo'],
         ru=('Диагностический канал', 'RTT или SWO показывают, что прошивка делает между остановками; сценарий DDTT они не заменяют, но помогают объяснить FAIL.'),
         en=('Diagnostic channel', 'RTT or SWO show what the firmware does between stops; they do not replace a DDTT scenario but help explain a FAIL.')),
    dict(id='autonomous', nodes=['stand-loop', 'results', 'develop'],
         ru=('Автономный стенд', 'Конечные циклы неизменного комплекта, разбор попыток; найденная проблема — отдельный цикл develop.'),
         en=('Autonomous stand', 'Finite cycles of an immutable bundle and attempt review; a discovered issue becomes a separate develop cycle.')),
]

API3_GENERAL = {
    'ru': ('Обычный def выполняет операции по очереди. В async def навигация (reach, step, until, finish, resume, reset) '
           'и call ожидаются через await; resume(sync=False) отпускает цель, await wait/halt ждут с таймаутом. '
           'Чтение, запись, проверки и записи журнала await не требуют. Выражения не вызывают функции цели.'),
    'en': ('An ordinary def runs operations in order. In async def, navigation (reach, step, until, finish, resume, reset) '
           'and call are awaited; resume(sync=False) lets the target go and await wait/halt wait with a timeout. '
           'Reads, writes, checks and journal records need no await. Expressions never call target functions.'),
}

# API groups: methods with first release, API 3 notes, recommended and discouraged fragments.
API = [
    dict(id='scenario', methods=[('case', '0.1.0-rc.1'), ('test', '0.3.0')],
         cards=['case', 'test'],
         ru=dict(title='Сценарий: def и async def',
                 summary='Декоратор объявляет сценарий; форма функции выбирает режим исполнения.',
                 api3='def сохраняет синхронную форму. async def — когда цель должна работать без остановки.',
                 good='Синхронный сценарий для конфигурации и ветвлений, асинхронный — для живого окна с halt в finally.',
                 bad='Навигация без await в async def: следующая операция с целью будет отклонена. Переводить работающий def в async без причины не нужно.'),
         en=dict(title='Scenario: def and async def',
                 summary='The decorator declares a scenario; the function form selects the execution mode.',
                 api3='def keeps the synchronous form. Use async def when the target must run without stopping.',
                 good='A synchronous scenario for configuration and branches, an asynchronous one for a live window with halt in finally.',
                 bad='Navigation without await in async def: the next target operation is refused. Do not convert a working def to async without a reason.'),
         good='''from stm32_gdbtest import case

@case("HW_BOOT", timeout_s=30, labels=("boot",))
def boot(t):
    t.reach("main")
    t.check("SystemCoreClock", t.read("SystemCoreClock"), 16_000_000)

@case("HW_LIVE", timeout_s=20)
async def live(t):
    await t.reach("app_loop")
    t.resume(sync=False)
    try:
        waited = await t.wait(timeout=0.2)
        t.check("still running", waited["outcome"], "timeout")
    finally:
        await t.halt(timeout=2)''',
         bad='''@case("HW_LIVE")
async def live(t):
    t.reach("app_loop")      # no await
    t.resume(sync=False)     # refused: unawaited_operation'''),
    dict(id='navigation', methods=[('reach', '0.1.0-rc.1'), ('step', '0.3.0'), ('until', '0.3.0'), ('finish', '0.3.0')],
         cards=['reach', 'step', 'until', 'finish'],
         ru=dict(title='Навигация: reach, step, until, finish',
                 summary='Дойти до функции или строки, сделать шаг, выполнить до возврата. Каждая операция возвращает остановку.',
                 api3='В async def — await. Условие reach вычисляется без вызовов функций цели.',
                 good='Условие задаётся выражением над данными; finish возвращает в вызывающий кадр.',
                 bad='Вызов функции в условии отклоняется (expression_call_forbidden). Цикл step вместо reach с условием тратит время и точки.'),
         en=dict(title='Navigation: reach, step, until, finish',
                 summary='Run to a function or line, step, run until return. Each operation returns the stop.',
                 api3='Use await in async def. A reach condition is evaluated without calling target functions.',
                 good='The condition is an expression over data; finish returns to the calling frame.',
                 bad='A function call in a condition is refused (expression_call_forbidden). A step loop instead of reach with a condition wastes time and points.'),
         good='''t.reach("board_adc_sample", condition="board_adc_sequences == 3")
t.reach("app_step")
t.finish()
t.check("returned to the caller", t.frames()["frames"][0]["function"], "app_receiver_step")
t.until("app_loop")
t.step(3)

# async def
await t.reach("app_step")
await t.finish()''',
         bad='''t.reach("board_adc_sample", condition="board_adc_ready()")   # hidden call: refused
while t.read("board_adc_sequences") < 3:
    t.step()                                                     # use reach with a condition'''),
    dict(id='live-window', methods=[('resume', '0.3.0'), ('wait', '0.5.0'), ('halt', '0.5.0')],
         cards=['resume', 'wait', 'halt'],
         ru=dict(title='Живое окно: resume, wait, halt',
                 summary='Отпустить цель, ждать остановки с таймаутом, остановить с подтверждением.',
                 api3='resume(sync=False), wait и halt — только async def; таймаут обязателен. В def resume() блокирует до остановки.',
                 good='halt — в finally: таймаут wait цель не останавливает. Поколение (generation) связывает остановку с окном.',
                 bad='Пока цель работает, доступ к памяти отклоняется (not_stopped). Без finally таймаут оставит цель работающей.'),
         en=dict(title='Live window: resume, wait, halt',
                 summary='Let the target run, wait for a stop with a timeout, halt with confirmation.',
                 api3='resume(sync=False), wait and halt are async def only; the timeout is mandatory. In def, resume() blocks until a stop.',
                 good='halt goes into finally: a wait timeout does not stop the target. The generation links a stop to its window.',
                 bad='Memory access while the target runs is refused (not_stopped). Without finally, a timeout leaves the target running.'),
         good='''@case("HW_WINDOW")
async def window(t):
    await t.reach("idle")
    started = t.resume(sync=False)
    try:
        waited = await t.wait(timeout=0.2)
        t.check("no stop yet", waited["outcome"], "timeout")
    finally:
        stopped = await t.halt(timeout=2)
    t.check("same window", stopped["generation"], started["generation"])
    t.check("memory readable", t.read("counter"), 3)''',
         bad='''await t.reach("idle")
t.resume(sync=False)
value = t.read("counter")      # refused: not_stopped
await t.wait(timeout=5)        # no finally/halt: a timeout leaves the target running'''),
    dict(id='data', methods=[('read', '0.3.0'), ('write', '0.3.0')],
         cards=['read', 'write'],
         ru=dict(title='Данные: read и write',
                 summary='Чтение объекта по имени или выражению, запись значения или таблицы записей.',
                 api3='await не нужен. Правая часть write вычисляется один раз; выражения без вызовов функций.',
                 good='Поля структуры — одним чтением; несколько записей — таблицей в нужном порядке.',
                 bad='Регистры периферии через общие методы: составное чтение задевает соседние регистры, RMW скрывает эффекты. Для регистров — mmio.'),
         en=dict(title='Data: read and write',
                 summary='Read an object by name or expression, write a value or a table of writes.',
                 api3='No await. The write right-hand side is evaluated once; expressions never call functions.',
                 good='Read structure fields in one call; several writes as a table in the required order.',
                 bad='Peripheral registers through general methods: a compound read touches neighbours and RMW hides effects. Use mmio for registers.'),
         good='''ticks = t.read("app_state.ticks")
state = t.read("app_state", fields={"ticks": None, "led": None})
t.write("app_delay", 100)
t.write([("app_state.mode", "APP_MODE_BLINK"), ("app_delay", 100)])''',
         bad='''t.write("ADC1->CR", t.read("ADC1->CR") | 4)   # register via data methods: use t.mmio
t.write("app_delay", "compute_delay()")        # hidden call: refused'''),
    dict(id='memory', methods=[('evaluate', '0.3.0'), ('memory', '0.3.0'), ('symbol', '0.3.0')],
         cards=['evaluate', 'memory', 'symbol'],
         ru=dict(title='Выражения и память: evaluate, memory, symbol',
                 summary='Значение выражения нужного типа; байты SRAM/Flash по адресу символа.',
                 api3='await не нужен. memory ограничена окнами SRAM и Flash; неполный ответ — ошибка.',
                 good='Снимок объекта байтами до воздействия и восстановление после.',
                 bad='memory по адресу периферии отклоняется: это не обход MMIO. Вызов функции внутри evaluate отклоняется — используйте call.'),
         en=dict(title='Expressions and memory: evaluate, memory, symbol',
                 summary='An expression value of the required type; SRAM/Flash bytes at a symbol address.',
                 api3='No await. memory is limited to SRAM and Flash windows; a short response is an error.',
                 good='Snapshot an object as bytes before an intervention and restore it afterwards.',
                 bad='memory at a peripheral address is refused: it is not an MMIO bypass. A function call inside evaluate is refused — use call.'),
         good='''version = t.evaluate("app_info.version", as_type=str)
state = t.symbol("app_state")
snapshot = t.memory(state["address"], state["size"])
t.call("app_step", timeout=2)               # changes app_state
t.memory(state["address"], snapshot)''',
         bad='''t.memory(0x40020014, 4)           # peripheral window: refused
t.evaluate("crc32(buffer, 16)")   # hidden call: refused'''),
    dict(id='mmio', methods=[('mmio.read', '0.5.0'), ('mmio.write', '0.5.0')],
         cards=['mmio'],
         ru=dict(title='Регистры: mmio.read и mmio.write',
                 summary='Один прямой запрос к регистру по имени из снимка SVD с проверкой прав и эффектов.',
                 api3='Новое в 0.5.0, await не нужен. Нужен [mmio] svd в session.toml; эффекты чтения и записи — только с allow_effects=True.',
                 good='Атомарная установка через BSRR; флаги W1C — явной маской только своих битов.',
                 bad='RMW всего регистра теряет атомарность; чтение регистра с эффектом без согласия отклоняется. Повтор после потери ACK запрещён.'),
         en=dict(title='Registers: mmio.read and mmio.write',
                 summary='One direct request to a register named in the SVD snapshot, with access-right and effect checks.',
                 api3='New in 0.5.0, no await. Needs [mmio] svd in session.toml; read and write effects require allow_effects=True.',
                 good='Atomic set through BSRR; W1C flags with an explicit mask of your own bits.',
                 bad='A whole-register RMW loses atomicity; reading a register with an effect without consent is refused. No retry after a lost ACK.'),
         good='''idr = t.mmio.read("GPIOC.IDR")                  # int, one direct read
ack = t.mmio.write("GPIOC.BSRR", 1 << 13)         # atomic set, no RMW
t.check("acknowledged", ack["acknowledged"], True)
flags = t.mmio.read("DMA2.LISR")
t.mmio.write("DMA2.LIFCR", flags & 0x3D, allow_effects=True)   # W1C: only stream 0 bits''',
         bad='''t.mmio.write("GPIOC.ODR", t.mmio.read("GPIOC.ODR") | (1 << 13))   # RMW: not atomic
data = t.mmio.read("USART2.DR")         # readAction in the SVD: effect_consent_required
try:
    data = t.mmio.read("USART2.DR", allow_effects=True)
except ApiError:
    data = t.mmio.read("USART2.DR", allow_effects=True)    # retry: the FIFO may be drained'''),
    dict(id='checks', methods=[('check', '0.1.0-rc.1'), ('within, near, one_of, matches', '0.3.0'), ('refused', '0.3.0')],
         cards=['check', 'matchers', 'refused'],
         ru=dict(title='Проверки: check, сопоставители, refused',
                 summary='Именованная проверка или таблица проверок; ожидаемый отказ API с кодом.',
                 api3='Без изменений, await не нужен.',
                 good='Ожидания — именами CMSIS и сопоставителями; отказ — через refused с кодом и эффектом.',
                 bad='assert и голый try/except не дают имени в отчёте и прячут код отказа. Магические числа вместо имён CMSIS не проверяются контрактом.'),
         en=dict(title='Checks: check, matchers, refused',
                 summary='A named check or a table of checks; an expected API refusal with its code.',
                 api3='Unchanged, no await.',
                 good='Expectations by CMSIS names and matchers; a refusal through refused with code and effect.',
                 bad='assert and a bare try/except give no name in the report and hide the refusal code. Magic numbers instead of CMSIS names escape the contract.'),
         good='''from stm32_gdbtest import within, near, one_of

t.check("VDDA, mV", t.read("board_adc_reading.vdda_mv"), within(2800, 3600))
t.check("stand backend", t.profile.stand["backend"], one_of("openocd", "jlink"))
t.check([
    ("PA5 output", "GPIOA->MODER & GPIO_MODER_MODER5", "GPIO_MODER_MODER5_0"),
    ("timer running", "TIM3->CR1 & TIM_CR1_CEN"),
])
with t.refused("unsupported_argument", effect="none"):
    t.call("app_step", object())''',
         bad='''assert t.read("app_state.ticks") == 1                     # no named check
try:
    t.call("app_step", object())
except Exception:
    pass                                                    # hides the code and the effect
t.check("mode", t.read("GPIOA->MODER") & 0xC00, 0x400)    # magic numbers'''),
    dict(id='injection', methods=[('ret', '0.3.0'), ('call', '0.3.0')],
         cards=['ret', 'call'],
         ru=dict(title='Инъекции: ret и call',
                 summary='Подменить возврат текущей функции; вызвать функцию прошивки и получить результат.',
                 api3='call в async — await; timeout= ограничивает вызов (0.5.0). ret не исполняет тело функции.',
                 good='После ret продолжите до обработки возврата и проверьте потребление, пропущенные эффекты и следующий вход (пример tests/controlled-input). Readback SRAM не доказывает потребление. ret проверяет реакцию вызывающего кода; call — с явным таймаутом. В кандидате 0.6.0 namespace/static требуют единственного символа; A4.2 допускает явный this и точную signature; A4.3a — Pointer/Reference с проверкой типов и SRAM. A4.3b корректирует this/Pointer/Reference к однозначной невиртуальной базе по DWARF; при преобразовании Pointer count=1. Сравните адрес подобъекта с независимым эталоном. Count не ограничивает тело функции. Сначала outcome/return_state, затем return_value; логическое время задаётся аргументом.',
                 bad='Вызов внутри выражения отклоняется; вызов без таймаута ограничен только лимитом сценария. ret не восстанавливает прерванный call. Программная подмена не доказывает физическое нажатие или отказ периферии.'),
         en=dict(title='Injection: ret and call',
                 summary='Replace the return of the current function; call a firmware function and get its result.',
                 api3='call is awaited in async; timeout= bounds the call (0.5.0). ret does not execute the function body.',
                 good='After ret, continue to caller processing and check consumption, skipped effects and the next input (tests/controlled-input). SRAM readback does not prove consumption. ret checks the caller; call uses an explicit timeout. In the 0.6.0 candidate namespace/static require one symbol; A4.2 supports explicit this and exact signature; A4.3a adds Pointer/Reference with type/SRAM checks. A4.3b adjusts this/Pointer/Reference to an unambiguous non-virtual DWARF base; converting Pointer requires count=1. Compare the subobject address with an independent oracle. Count does not constrain the function body. Check outcome/return_state before return_value; pass logical time as an argument.',
                 bad='A call inside an expression is refused; a call without a timeout is bounded only by the scenario limit. ret does not restore an interrupted call. Software substitution does not establish a physical button press or peripheral failure.'),
         good='''t.reach("sample_input")
result = t.ret(1)
t.check("forced", result["outcome"], "forced")
t.reach("after_processing")  # Caller must run before checking consumption.
t.check("caller consumed the value", t.read("input_state.consumed"), 1)

value = t.call("app_checksum", 7, timeout=2)       # async def: await t.call(...)
t.check("returned", value["outcome"], "returned")
t.check("value available", value["return_state"], "available")
t.check("checksum(7)", value["return_value"], 22)

# Separate tests/logical-time ELF: ticks are not host seconds.
t.reach("ready")
t.call("start", 100, 10, timeout=2)
result = t.call("poll", 110, timeout=2)
t.check("returned", result["outcome"], "returned")
t.check("value available", result["return_state"], "available")
t.check("DONE", result["return_value"], 2)''',
         bad='''t.check("DONE", t.call("poll", 110), 2)   # dict is not the returned number

t.read("app_checksum(7)")   # refused: expression_call_forbidden
t.call("app_wait_forever")   # no timeout: only the scenario limit stops it
t.call("app_log", "text")   # string argument: unsupported_argument
t.call("demo::overloaded", 1)   # ambiguous_function, no overload guessing
t.call("Probe::add", 1)   # unsupported_method: explicit this is required'''),
    dict(id='points', methods=[('breakpoint', '0.1.0-rc.1'), ('watch', '0.3.0'), ('Point', '0.3.0'), ('clear', '0.1.0-rc.1')],
         cards=['breakpoint', 'watch', 'point', 'clear'],
         ru=dict(title='Точки: breakpoint, watch, Point, clear',
                 summary='Точки останова и наблюдения как объекты Point с состоянием и снятием.',
                 api3='Без изменений; условие точки вычисляется без вызовов функций.',
                 good='watch и breakpoint — контекстом with или с явным remove().',
                 bad='gdb.execute("break …") обходит Target: точка не учитывается и не снимается. clear() удаляет и защиту от отказов — только намеренно.'),
         en=dict(title='Points: breakpoint, watch, Point, clear',
                 summary='Breakpoints and watchpoints as Point objects with state and removal.',
                 api3='Unchanged; a point condition is evaluated without function calls.',
                 good='watch and breakpoint inside a with block or with an explicit remove().',
                 bad='gdb.execute("break …") bypasses Target: the point is neither tracked nor removed. clear() also removes fault guards — only on purpose.'),
         good='''with t.watch("app_state.ticks"):
    t.resume()

point = t.breakpoint("board_led_toggle")
t.reach("app_loop")
t.check("point is active", point.active, True)
point.remove()''',
         bad='''import gdb
gdb.execute("break board_led_toggle")   # not tracked, not cleaned up
t.clear()                               # also removes fault guards'''),
    dict(id='journal', methods=[('record', '0.3.0'), ('records', '0.3.0'), ('skip', '0.4.0')],
         cards=['record', 'records', 'skip'],
         ru=dict(title='Журнал и SKIP: record, records, skip',
                 summary='Произвольные данные в отчёт; выборка своих записей; завершение неприменимого сценария.',
                 api3='Без изменений. Записи на диск — при [results] capture = true; MMIO добавляет записи журнала.',
                 good='Сначала record, затем check: сохраняйте сырые выборки, единицы, прогрев и пригодность. В counter-cost время запроса GDB отделено от учебных тиков; максимум выборки — не WCET. В external-capture отдельно проверяются READY/drain, полнота и временные опоры; анализ не переписывает исход сценария.',
                 bad='print не попадает в отчёт. Неполные данные нельзя заменять нулём; расход внутри интервала не равен полному возмущению. SKIP не скрывает ошибки API; exit 0 источника не гарантирует полноту записи.'),
         en=dict(title='Journal and SKIP: record, records, skip',
                 summary='Arbitrary data into the report; selecting your records; ending a non-applicable scenario.',
                 api3='Unchanged. Records reach disk with [results] capture = true; MMIO adds journal records.',
                 good='Record before check: keep raw samples, units, warmup and eligibility. In counter-cost GDB request time is separate from model ticks; a sample maximum is not WCET. external-capture checks READY/drain, completeness and clock anchors separately; analysis never rewrites the scenario outcome.',
                 bad='print does not reach the report. Missing data is not zero; in-interval cost is not total perturbation. SKIP must not hide API errors; source exit 0 does not establish capture completeness.'),
         good='''t.record("adc.sample", {"vdda_mv": t.read("board_adc_reading.vdda_mv")})
samples = [row["data"]["vdda_mv"] for row in t.records("adc.sample")]
t.check("enough samples", len(samples) >= 2, True)
if not t.profile.get("user.sample_step", True):
    t.skip("sample_step disabled in api.toml")''',
         bad='''print(t.read("board_adc_reading.vdda_mv"))   # not in the report
try:
    t.reach("board_adc_sample")
except Exception:
    t.skip("no ADC")                          # SKIP hides an error'''),
    dict(id='context', methods=[('profile', '0.1.0-rc.1'), ('registers', '0.3.0'), ('frames', '0.3.0'), ('locals, arguments', '0.3.0')],
         cards=['profile', 'registers', 'frames', 'locals'],
         ru=dict(title='Контекст: profile, registers, frames, locals',
                 summary='Данные прогона и проекта; регистры ядра, стек вызовов, локальные переменные и аргументы.',
                 api3='Без изменений, await не нужен.',
                 good='Параметры проекта — profile.get с умолчанием; аргументы — в остановленном кадре.',
                 bad='Жёсткие числа в сценарии вместо параметров профиля; чтение цепочки индексов падает, если раздела нет.'),
         en=dict(title='Context: profile, registers, frames, locals',
                 summary='Run and project data; core registers, call stack, locals and arguments.',
                 api3='Unchanged, no await.',
                 good='Project parameters through profile.get with a default; arguments in the stopped frame.',
                 bad='Hard-coded numbers instead of profile parameters; an index chain fails when a section is missing.'),
         good='''count = t.profile.get("user.measurement.count", 10)
core = t.registers("pc", "sp")
t.record("core", core)
t.check("top frame", t.frames(limit=8)["frames"][0]["function"], "app_step")
t.reach("app_step")
t.check("mode argument", t.arguments()["values"]["mode"], t.evaluate("APP_MODE_BLINK"))''',
         bad='''count = t.profile["user"]["measurement"]["count"]   # fails without the section
t.check("delay", t.read("app_delay"), 100)            # expectation not taken from the profile'''),
    dict(id='low-level', methods=[('reset', '0.3.0'), ('execute', '0.3.0')],
         cards=['reset', 'execute'],
         ru=dict(title='Сброс и команды GDB: reset, execute',
                 summary='Сброс цели с остановкой; произвольная команда GDB как низкоуровневый выход.',
                 api3='reset в async — await, эмулятор отклоняет. execute в async def отклоняется (unsupported_async_command).',
                 good='После reset — проверка исхода и явная навигация.',
                 bad='execute обходит гарантии API: не меняйте через него данные и не управляйте исполнением.'),
         en=dict(title='Reset and GDB commands: reset, execute',
                 summary='Reset the target with a halt; an arbitrary GDB command as a low-level escape.',
                 api3='reset is awaited in async; emulators refuse it. execute is refused in async def (unsupported_async_command).',
                 good='After reset, check the outcome and navigate explicitly.',
                 bad='execute bypasses API guarantees: do not change data or control execution through it.'),
         good='''result = t.reset()                  # async def: await t.reset()
t.check("halted after reset", result["outcome"], "halted")
t.reach("main")''',
         bad='''t.execute("set var app_delay = 0")   # use t.write
t.execute("continue")                # use resume; refused in async def'''),
    dict(id='errors', methods=[('ApiError', '0.3.0'), ('CheckFailed', '0.3.0'), ('RecordError', '0.3.0')],
         cards=['api-error', 'check-failed', 'record-error'],
         ru=dict(title='Ошибки: ApiError, CheckFailed, RecordError',
                 summary='Отказ операции с кодом, стадией и эффектом; проваленная проверка; ошибка журнала.',
                 api3='Новые коды API 3: unawaited_operation, already_awaited, operation_timeout, halt_timeout, expression_call_forbidden, unsupported_async_command, call_incomplete.',
                 good='Ожидаемый отказ — refused; причина сохраняется в __cause__.',
                 bad='Перехват и подавление ApiError превращает отказ в ложный PASS.'),
         en=dict(title='Errors: ApiError, CheckFailed, RecordError',
                 summary='An operation refusal with code, stage and effect; a failed check; a journal error.',
                 api3='New API 3 codes: unawaited_operation, already_awaited, operation_timeout, halt_timeout, expression_call_forbidden, unsupported_async_command, call_incomplete.',
                 good='An expected refusal goes through refused; the cause stays in __cause__.',
                 bad='Catching and suppressing ApiError turns a refusal into a false PASS.'),
         good='''with t.refused("command_failed") as failure:
    t.evaluate("no_such_symbol")
t.check("cause kept", failure.error.__cause__ is not None)''',
         bad='''from stm32_gdbtest import ApiError
try:
    t.ret(1 << 40)
except ApiError:
    pass                      # a refusal becomes a false PASS'''),
]

REMOVED = [('value', 'read, evaluate'), ('fields', 'read(path, fields=…), check(rows)'),
           ('set_value', 'write'), ('force_return', 'ret')]

# Card -> (signature, first release, API 3 note RU, EN); ¹ marks a base form extended in 0.3.0.
CARDS = {
 'case': ('case(identifier, *, timeout_s=20, labels=(), contracts=())', '0.1.0-rc.1', 'def или async def', 'def or async def'),
 'test': ('test(identifier, *, timeout_s=20, labels=(), contracts=())', '0.3.0', 'как case', 'as case'),
 'reach': ('reach(location, condition=None) -> dict', '0.1.0-rc.1¹', 'await в async', 'await in async'),
 'step': ('step(count=1, *, unit="source", mode="into") -> dict', '0.3.0', 'await в async', 'await in async'),
 'until': ('until(location=None) -> dict', '0.3.0', 'await в async', 'await in async'),
 'finish': ('finish() -> dict', '0.3.0', 'await в async', 'await in async'),
 'resume': ('resume(*, sync=True) -> dict', '0.3.0', 'sync=False — 0.5.0', 'sync=False — 0.5.0'),
 'wait': ('await wait(*, timeout) -> dict', '0.5.0', 'только async', 'async only'),
 'halt': ('await halt(*, timeout) -> dict', '0.5.0', 'только async', 'async only'),
 'read': ('read(path, *, fields=None, start=0, count=None)', '0.3.0', 'без вызовов в выражении', 'no calls in expressions'),
 'write': ('write(path, value, *, verify=True) -> dict; write(rows) -> list', '0.3.0', 'без вызовов в выражении', 'no calls in expressions'),
 'evaluate': ('evaluate(expression, *, as_type=None)', '0.3.0', 'без вызовов в выражении', 'no calls in expressions'),
 'memory': ('memory(address, size | data, *, verify=None)', '0.3.0', 'без изменений', 'unchanged'),
 'symbol': ('symbol(name) -> dict', '0.3.0', 'без изменений', 'unchanged'),
 'mmio': ('mmio.read(name, *, allow_effects=False) -> int; mmio.write(name, value, *, allow_effects=False) -> dict', '0.5.0', 'новое', 'new'),
 'check': ('check(name, actual, expected=True); check(rows) -> int', '0.1.0-rc.1¹', 'без вызовов в выражении', 'no calls in expressions'),
 'matchers': ('within(low, high), near(value, tolerance), one_of(*options), matches(pattern)', '0.3.0', 'без изменений', 'unchanged'),
 'refused': ('with refused(code, *, name=None, **details) as refusal', '0.3.0', 'без изменений', 'unchanged'),
 'ret': ('ret(value=None) -> dict', '0.3.0', 'без изменений', 'unchanged'),
 'call': ('call(function, *args, this=None, signature=None, timeout=None) -> dict', '0.3.0', 'await в async; timeout=', 'await in async; timeout='),
 'breakpoint': ('breakpoint(location, temporary=False, *, condition=None, ignore_count=0) -> Point', '0.1.0-rc.1', 'без изменений', 'unchanged'),
 'watch': ('watch(path) -> Point', '0.3.0', 'без изменений', 'unchanged'),
 'point': ('Point: active, hit_count, condition; enable(), disable(), remove(), with', '0.3.0', 'без изменений', 'unchanged'),
 'clear': ('clear() -> None', '0.1.0-rc.1', 'без изменений', 'unchanged'),
 'record': ('record(name, data) -> None', '0.3.0', 'без изменений', 'unchanged'),
 'records': ('records(name=None, *, require_complete=True) -> list[dict]', '0.3.0', '0.6.0: явное частичное чтение', '0.6.0: explicit partial reads'),
 'skip': ('skip(reason) -> NoReturn', '0.4.0', 'без изменений', 'unchanged'),
 'profile': ('profile: Profile', '0.1.0-rc.1¹', 'без изменений', 'unchanged'),
 'registers': ('registers(*names, frame=None) -> dict', '0.3.0', 'без изменений', 'unchanged'),
 'frames': ('frames(limit=16) -> dict', '0.3.0', 'без изменений', 'unchanged'),
 'locals': ('locals(frame=None) -> dict; arguments(frame=None) -> dict', '0.3.0', 'без изменений', 'unchanged'),
 'reset': ('reset() -> dict', '0.3.0', 'await в async', 'await in async'),
 'execute': ('execute(command) -> str', '0.3.0', 'отклоняется в async', 'refused in async'),
 'api-error': ('ApiError: details, code, __cause__', '0.3.0', 'новые коды', 'new codes'),
 'check-failed': ('CheckFailed(ApiError, AssertionError)', '0.1.0-rc.1¹', 'без изменений', 'unchanged'),
 'record-error': ('RecordError(ValueError)', '0.3.0', 'без изменений', 'unchanged'),
}

# Card -> displayed name when it differs from the file name.
CARD_NAMES = {'matchers': 'within, near, one_of, matches', 'point': 'Point', 'locals': 'locals, arguments',
        'api-error': 'ApiError', 'check-failed': 'CheckFailed', 'record-error': 'RecordError', 'mmio': 'mmio.read, mmio.write'}
