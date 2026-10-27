"""RU: TECH-024: счётчик, пригодность разности и расходы наблюдения.
EN: TECH-024: counter deltas, eligibility and observation costs.
"""
import time
import statistics
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


# Полный wrap нельзя различить по двум значениям; граница должна прийти извне.
@case("HW_EMU_COUNTER_WRAP", timeout_s=30, labels=("emulator", "counter"))
def wrap(t):
    with restored(t):
        t.call("difference", 250, 5, 11, 1, timeout=2)
        got = [t.read("state.valid"), t.read("state.delta")]
        t.record("wrap", {"before": 250, "after": 5, "upper": 11, "actual": got})
        t.check("разность через wrap", got, [1, 11])
        t.call("difference", 7, 7, 0, 1, timeout=2)
        t.check("достоверный ноль", [t.read("state.valid"), t.read("state.delta")], [1, 0])
        t.call("difference", 0, 255, 255, 1, timeout=2)
        t.check("последний допустимый прирост", t.read("state.delta"), 255)


# Неизвестное не маскируется нулём: проверяем отдельный valid.
@case("HW_EMU_COUNTER_UNKNOWN", timeout_s=30, labels=("emulator", "counter"))
def unknown(t):
    with restored(t):
        actual = []

        # Полный оборот, потерянная выборка, нарушение границы, неверная разрядность.
        for args in ((7, 7, 256, 1), (7, 9, 2, 0), (7, 12, 4, 1), (256, 0, 1, 1)):
            actual.append(value(t, "difference", *args))
        t.record("eligibility", {"valid": actual})
        t.check("неизвестные отклонены", actual, [0, 0, 0, 0])


# Пустой контроль измеряет часть расходов внутри интервала; полные расходы больше.
@case("HW_EMU_COUNTER_COST", timeout_s=30, labels=("emulator", "counter"))
def cost(t):
    with restored(t):
        t.call("measure", 0, timeout=2)
        empty = [t.read("state.gross"), t.read("state.net"), t.read("state.observer")]
        t.record("empty", {"gross": empty[0], "net": empty[1], "observer": empty[2], "unit": "model_tick"})
        t.check("пустой контроль", empty, [3, 0, 6])
        t.call("measure", 4, timeout=2)
        got = [t.read("state.gross"), t.read("state.net"), t.read("state.observer"), t.read("state.clock")]
        t.record("work", {"values": got, "unit": "model_tick", "net_budget": 28})
        t.check("работа и полные расходы", got, [31, 28, 6, 34])
        before = t.memory(t.symbol("state")["address"], t.symbol("state")["size"])
        t.check("слишком большая работа", value(t, "measure", 17), 0)
        t.check("отказ без изменения", t.memory(t.symbol("state")["address"], len(before)), before)


# Реальное время запроса ПК включает GDB и транспорт: только описательная статистика.
@case("HW_EMU_COUNTER_TRANSPORT", timeout_s=30, labels=("emulator", "counter"))
def transport(t):
    with restored(t):
        samples = []

        # Первую из шести выборок заранее исключаем как прогрев, но сохраняем все.
        for index in range(6):
            begin = time.perf_counter_ns()
            result = t.call("measure", 0, timeout=2)
            elapsed = time.perf_counter_ns() - begin
            samples.append(elapsed)
            t.check("вызов завершён", result["outcome"], "returned")
        used = samples[1:]
        t.record("host_latency", {"samples_ns": samples, "warmup_count": 1,
                                  "median_ns": statistics.median(used), "max_ns": max(used),
                                  "scope": "host_gdb_roundtrip", "wcet": False})
        t.check("полнота выборки", len(samples), 6)
        t.check("монотонные часы", all(item >= 0 for item in samples), True)
