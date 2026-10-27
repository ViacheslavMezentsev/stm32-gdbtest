"""RU: TECH-022: явное логическое время, без реальных таймеров.
EN: TECH-022: explicit logical time, without physical timers.
"""
from contextlib import contextmanager
from stm32_gdbtest import case


# Полный снимок и восстановление даже после намеренного FAIL.
@contextmanager
def restored(t):
    # Снимок принадлежит только нейтральному POD-объекту, без указателей и внешних ресурсов.
    t.reach("ready")
    symbol = t.symbol("state")
    saved = t.memory(symbol["address"], symbol["size"])
    try:
        yield
    finally:
        t.memory(symbol["address"], saved)
        t.check("полное восстановление", t.memory(symbol["address"], len(saved)), saved)
        t.record("restoration", {"verified": True, "bytes": len(saved)})


# call возвращает описание операции, а не непосредственно значение функции.
def value(t, function, *args):
    result = t.call(function, *args, timeout=2)
    t.check("вызов вернулся", result["outcome"], "returned")
    t.check("значение доступно", result["return_state"], "available")
    return result["return_value"]


# Снять все числа до проверки: исходный FAIL не должен уничтожать наблюдения.
def observe(t, times):
    values = []

    # У каждого момента есть заранее заданное ожидаемое состояние.
    for now in times:
        values.append(value(t, "poll", now))
    t.record("timeline", {"ticks": list(times), "phases": values})
    return values


# Точное включение границы и пропуск момента опроса — разные случаи.
@case("HW_EMU_TIME_THRESHOLD", timeout_s=30, labels=("emulator", "time"))
def threshold(t):
    with restored(t):
        t.check("start принят", value(t, "start", 100, 10), 1)
        got = observe(t, (109, 110, 111))
        t.check("порог включительно", got, [1, 2, 2])
        t.check("один успех", t.read("state.successes"), 1)
        t.call("model_reset")
        t.call("start", 100, 10)
        t.check("пропущенный порог", value(t, "poll", 111), 2)


# Числа ожиданий выписаны независимо: после FFFFFFF8 десять тиков дают 2.
@case("HW_EMU_TIME_WRAP", timeout_s=30, labels=("emulator", "time"))
def wrap(t):
    with restored(t):
        t.call("start", 0xfffffff8, 10)
        got = observe(t, (0xffffffff, 1, 2, 3))
        t.check("переход через ноль", got, [1, 1, 2, 2])
        t.check("один успех после переполнения", t.read("state.successes"), 1)


# После отказа нельзя сбрасывать объект: это скрыло бы остаток старого времени.
@case("HW_EMU_TIME_RETRY", timeout_s=30, labels=("emulator", "time"))
def retry(t):
    with restored(t):
        t.call("start", 100, 10)
        t.call("fail")
        t.call("fail")
        t.check("отказ устойчив", value(t, "poll", 1000), 3)
        t.check("отказ учтён один раз", t.read("state.failures"), 1)
        t.check("при отказе нет успеха", t.read("state.successes"), 0)
        t.call("start", 1000, 10)
        got = observe(t, (1009, 1010, 1011))
        t.check("новая эпоха после отказа", got, [1, 2, 2])
        t.call("start", 2000, 5)
        t.call("poll", 2006)

        # Итоговые счётчики проверяются независимо от промежуточных значений.
        t.check([
            ("три принятых старта", "state.attempts", 3),
            ("два успеха", "state.successes", 2),
            ("один отказ", "state.failures", 1)
        ])


# Отвергнутые старты не должны менять даже скрытые поля объекта.
@case("HW_EMU_TIME_REJECT", timeout_s=30, labels=("emulator", "time"))
def reject(t):
    with restored(t):
        symbol = t.symbol("state")
        saved = t.memory(symbol["address"], symbol["size"])

        # Проверить обе границы и максимальное беззнаковое значение.
        for delay in (0, 0x80000000, 0xffffffff):
            t.check("недопустимая задержка", value(t, "start", 0, delay), 0)
            t.check("отказ без изменений", t.memory(symbol["address"], symbol["size"]), saved)
        t.call("start", 42, 10)
        busy = t.memory(symbol["address"], symbol["size"])
        t.check("повторный start отклонён", value(t, "start", 77, 20), 0)
        t.check("активное состояние сохранено", t.memory(symbol["address"], symbol["size"]), busy)
        t.check("левый guard", t.read("state.guard_a"), 0x13579BDF)
        t.check("правый guard", t.read("state.guard_b"), 0x2468ACE0)
