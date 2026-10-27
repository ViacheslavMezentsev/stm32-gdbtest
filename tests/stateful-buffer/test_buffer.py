"""RU: TECH-021: остаточное состояние и выбранные порядки событий, без периферии.
EN: TECH-021: residual state and selected event order, without peripherals.
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


# Передать длину и полезные байты по одному.
def packet(t, length, first):
    t.call("feed", length)

    # Полезная нагрузка задаётся независимо от реализации.
    for value in range(first, first + length):
        t.call("feed", value)


# Сохранить свидетельство до проверки, способной завершить сценарий.
def observe(t, fields):
    values = {name: t.read("state." + name) for name in fields}
    t.record("observation", values)
    return values


# Следующий пакет отличается от предыдущего длиной и содержимым.
@case("HW_EMU_NEXT_COMPLETE", timeout_s=30, labels=("emulator", "state"))
def next_complete(t):
    with restored(t):
        packet(t, 3, 10)
        t.check("первый пакет опубликован", t.read("state.packets"), 1)
        packet(t, 2, 70)
        got = observe(t, ("packets", "published_size", "published[0]", "published[1]", "used"))
        t.check("новый пакет без остатка", got,
                {"packets": 2, "published_size": 2, "published[0]": 70, "published[1]": 71, "used": 0})


# Таймаут частичного пакета не должен загрязнить следующий.
@case("HW_EMU_NEXT_TIMEOUT", timeout_s=30, labels=("emulator", "state"))
def next_timeout(t):
    with restored(t):
        t.call("feed", 4)
        t.call("feed", 20)
        t.check("частичный пакет не опубликован", t.read("state.packets"), 0)
        t.call("expire")
        packet(t, 2, 80)
        got = observe(t, ("packets", "published_size", "published[0]", "published[1]"))
        t.check("пакет после таймаута", got,
                {"packets": 1, "published_size": 2, "published[0]": 80, "published[1]": 81})


# Проверить оба порядка kick/complete и границу сегмента.
@case("HW_EMU_RING_ORDER", timeout_s=60, labels=("emulator", "order"))
def ring_order(t):
    with restored(t):
        # Два детерминированных порядка событий, не перебор всех гонок.
        for order in (0, 1):
            t.call("model_reset")

            # Сдвинуть tail к концу кольца штатной отправкой.
            for value in range(6):
                t.call("enqueue", value)
            t.call("kick")
            t.call("complete")

            # Следующий пакет проходит через конец кольца.
            for value in range(10, 14):
                t.call("enqueue", value)
            t.call("kick")
            t.call("receive_error")
            t.check("RX не отменяет TX", t.read("state.busy"), 1)
            t.check("сегмент до границы кольца", t.read("state.inflight"), 2)
            if order == 0:
                t.call("kick")
            t.call("complete")
            if order == 1:
                t.call("kick")
            t.check("продолжение без задачи", t.read("state.inflight"), 2)
            t.call("complete")
            t.call("complete")
            got = [t.read(f"state.sent[{i}]") for i in range(10)]
            t.record("output", {"order": order, "bytes": got})
            t.check("порядок без потерь и дублей", got, [0, 1, 2, 3, 4, 5, 10, 11, 12, 13])

            # Независимые ожидания конечного состояния.
            t.check([
                ("число переданных байтов", "state.sent_size", 10),
                ("очередь пуста", "state.count", 0),
                ("передача завершена", "state.busy", 0)
            ])

        # Новый элемент нельзя включить в уже начатую передачу повторным kick.
        t.call("model_reset")
        t.call("enqueue", 41)
        t.call("kick")
        t.call("enqueue", 42)
        t.call("kick")
        observe(t, ("inflight", "count", "busy"))
        t.check("граница начатого сегмента неизменна", t.read("state.inflight"), 1)
        t.call("complete")
        t.call("complete")
        t.check("следующая передача", [t.read("state.sent[0]"), t.read("state.sent[1]")], [41, 42])
        t.check("левый guard", t.read("state.guard_a"), 0x13579BDF)
        t.check("правый guard", t.read("state.guard_b"), 0x2468ACE0)
