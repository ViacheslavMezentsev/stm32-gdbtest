"""RU: A5.1: подтверждаем потребление подмены, а не только успешную запись.
EN: A5.1: verify consumption, not just successful substitution.
"""
from contextlib import contextmanager
import hashlib
from stm32_gdbtest import case


# Снимок всего POD: сюда входят источник, состояние, счётчики и защитные слова.
@contextmanager
def restored(t):
    symbol = t.symbol("input_state")
    saved = t.memory(symbol["address"], symbol["size"])
    try:
        yield
    finally:
        t.memory(symbol["address"], saved)
        actual = t.memory(symbol["address"], len(saved))
        verified = actual == saved
        t.record("restoration", {"verified": verified, "bytes": len(saved),
                                 "before_sha256": hashlib.sha256(saved).hexdigest(),
                                 "after_sha256": hashlib.sha256(actual).hexdigest()})
        t.check("полное восстановление POD", actual, saved)


# Наблюдения сохраняются до сравнения, в том числе при намеренном FAIL.
def observe(t, method, supplied):
    data = {"method": method, "supplied": supplied, "scope": "software-input",
            "excluded": ["physical-signal", "peripheral-acquisition"],
            "consumed": t.read("input_state.consumed"), "active": t.read("input_state.active"),
            "reads": t.read("input_state.reads"), "cycles": t.read("input_state.cycles")}
    t.record("observation", data)
    t.check("левый сосед", t.read("input_state.left_guard"), 111)
    t.check("правый сосед", t.read("input_state.right_guard"), 222)
    return data


# Следующая штатная выборка должна увидеть исходный источник, а не остаток подмены.
async def next_sample(t, reads):
    await t.reach("before_sample")
    await t.reach("after_processing")

    # Все результаты следующего прохода проверяем вместе.
    t.check([
        ("следующий вход", "input_state.consumed", 0),
        ("следующая ветка", "input_state.active", 0),
        ("следующее чтение", "input_state.reads", reads),
        ("два цикла", "input_state.cycles", 2)
    ])


# Без воздействия штатный источник даёт ноль.
@case("HW_INPUT_BASELINE", timeout_s=20, labels=("emulator", "injection"))
async def baseline(t):
    await t.reach("before_refresh")
    with restored(t):
        await t.reach("after_processing")
        got = observe(t, "none", 0)
        t.check("без воздействия", [got["consumed"], got["active"], got["reads"]], [0, 0, 1])


# Запись после обновления должна дойти до приложения.
@case("HW_INPUT_SRAM", timeout_s=20, labels=("emulator", "injection"))
async def sram(t):
    await t.reach("before_refresh")
    with restored(t):
        await t.reach("before_sample")
        t.write("input_state.level", 1)
        t.check("запись применена", t.read("input_state.level"), 1)
        await t.reach("after_processing")
        got = observe(t, "sram", 1)
        t.check("подмена потреблена", [got["consumed"], got["active"], got["reads"]], [1, 1, 1])
        await next_sample(t, 2)


# Возврат меняем до первого побочного эффекта функции.
async def force_return(t, supplied):
    await t.reach("before_refresh")
    with restored(t):
        # Противоположный источник доказывает, что выбран именно возврат-подмена.
        t.write("input_state.source", 1 - supplied)
        await t.reach("sample_input")
        t.check("до тела функции", t.read("input_state.reads"), 0)
        result = t.ret(supplied)
        t.check("возврат подставлен", result["outcome"], "forced")
        t.check("типизированное значение", result["applied"], supplied)
        t.check("обработка ещё не шла", t.read("input_state.cycles"), 0)
        await t.reach("after_processing")
        got = observe(t, "ret", supplied)
        t.check("возврат потреблён", [got["consumed"], got["active"], got["reads"]], [supplied, supplied, 0])
        t.write("input_state.source", 0)
        await next_sample(t, 1)


# Положительный возврат при нулевом источнике.
@case("HW_INPUT_RET_HIGH", timeout_s=20, labels=("emulator", "injection"))
async def ret_high(t):
    await force_return(t, 1)


# Отрицательный контроль: нулевой возврат при единичном источнике.
@case("HW_INPUT_RET_LOW", timeout_s=20, labels=("emulator", "injection"))
async def ret_low(t):
    await force_return(t, 0)


# Намеренный FAIL: успешная запись не означает, что приложение её использовало.
@case("HW_INPUT_TOO_EARLY", timeout_s=20, labels=("emulator", "injection"))
async def too_early(t):
    await t.reach("before_refresh")
    with restored(t):
        t.write("input_state.level", 1)
        t.check("ранняя запись применена", t.read("input_state.level"), 1)
        await t.reach("after_processing")
        got = observe(t, "sram-too-early", 1)
        t.check("ранняя подмена потреблена", got["consumed"], 1)


# Намеренный ERROR после изменения: finally обязан вернуть все байты.
@case("HW_INPUT_EXCEPTION", timeout_s=20, labels=("emulator", "injection"))
async def exception(t):
    await t.reach("before_refresh")
    with restored(t):
        t.write("input_state.level", 1)
        t.record("interruption", {"stage": "before-consumption", "applied": t.read("input_state.level")})
        raise RuntimeError("controlled-input: intentional exception before consumption")
