"""RU: A5.3: подготовленный пакет в буфере опыта и повторное потребление обработчиком.
EN: A5.3: a prepared packet in an experiment-owned buffer and repeated handler consumption.
"""
from contextlib import contextmanager
import hashlib
from stm32_gdbtest import Pointer, case


# Изменяемые объекты опыта лежат подряд в секции .experiment в этом порядке.
LAYOUT = ("left_guard", "inject_buf", "right_guard", "rx_buf", "rx_len", "stats")
# Защитные слова вокруг буфера опыта; выход обработчика за границы их изменит.
GUARDS = (("left_guard", 0x11111111), ("right_guard", 0x22222222))
# Пакеты опыта: тип 0x21 с нагрузкой 3, 4, 5; тип 0x22 с нагрузкой 9; искажённая сумма.
PACKET_A = bytes([0x5F, 0x21, 3, 3, 4, 5, 0x8F])
PACKET_B = bytes([0x5F, 0x22, 1, 9, 0x8B])
PACKET_BAD = bytes([0x5F, 0x21, 3, 3, 4, 5, 0x90])
# Сигнатура обработчика задаёт точный тип указателя для Pointer.
SIGNATURE = "unsigned int(const unsigned char *, unsigned int)"
# Слои, которые этот опыт не проверяет.
EXCLUDED = ["dma", "peripheral-acquisition", "interrupt-context", "physical-signal"]


# Снимок всей секции опыта: оба буфера, защитные слова, длина и состояние обработчика.
@contextmanager
def restored(t):
    symbols = [t.symbol(name) for name in LAYOUT]
    start = symbols[0]["address"]
    offsets = [s["address"] - start for s in symbols]
    expected = [sum(s["size"] for s in symbols[:i]) for i in range(len(symbols))]
    t.check("секция опыта без промежутков", offsets, expected)
    size = expected[-1] + symbols[-1]["size"]
    saved = t.memory(start, size)
    try:
        yield
    finally:
        t.memory(start, saved)
        actual = t.memory(start, len(saved))
        verified = actual == saved
        t.record("restoration", {"verified": verified, "bytes": len(saved),
                                 "before_sha256": hashlib.sha256(saved).hexdigest(),
                                 "after_sha256": hashlib.sha256(actual).hexdigest()})
        t.check("полное восстановление секции опыта", actual, saved)


# Пакет кладётся только в буфер опыта; штатный rx_buf при этом не трогаем.
def put(t, packet):
    address = t.symbol("inject_buf")["address"]
    t.memory(address, packet)
    t.check("пакет в буфере опыта", t.memory(address, len(packet)), packet)


# Обработчик вызывается явно с указателем на буфер опыта и точной длиной.
async def deliver(t, packet):
    put(t, packet)
    result = await t.call("handle_packet", Pointer("inject_buf", count=len(packet)), len(packet),
                          signature=SIGNATURE, timeout=2)
    return result["return_value"]


# Наблюдения сохраняются до сравнений, в том числе при намеренном FAIL.
def observe(t, method, packets, returned):
    names = ("accepted", "rejected", "sequence", "last_type", "last_sum", "entries", "busy")
    data = {"method": method, "packets": [p.hex() for p in packets], "returned": returned,
            "scope": "software-buffer", "excluded": EXCLUDED}
    data.update({name: t.read("stats." + name) for name in names})
    t.record("observation", data)

    # Соседние слова и штатный буфер не должны пострадать.
    t.check([(f"защита {name}", name, value) for name, value in GUARDS])
    return data


# Следующий штатный пакет обрабатывается как обычно и не трогает буфер опыта.
async def next_packet(t, sequence, entries):
    before = t.memory(t.symbol("inject_buf")["address"], 16)
    await t.reach("after_processing")

    # Результаты штатного пакета проверяем вместе.
    t.check([
        ("штатный тип", "stats.last_type", 0x10),
        ("штатная нагрузка", "stats.last_sum", 3),
        ("номер пакета", "stats.sequence", sequence),
        ("входов в обработчик", "stats.entries", entries),
        ("обработчик свободен", "stats.busy", 0)
    ])
    t.check("буфер опыта не изменён штатным путём", t.memory(t.symbol("inject_buf")["address"], 16), before)


# Без воздействия штатный пакет проходит один раз.
@case("HW_BUFFER_BASELINE", timeout_s=20, labels=("emulator", "injection"))
async def baseline(t):
    await t.reach("before_receive")
    with restored(t):
        await t.reach("after_processing")
        got = observe(t, "none", [], [])
        counters = [got["accepted"], got["rejected"], got["sequence"], got["last_type"]]
        t.check("без воздействия", counters, [1, 0, 1, 0x10])


# Два пакета опыта подряд, затем штатный пакет: порядок и соседний путь сохраняются.
@case("HW_BUFFER_PACKETS", timeout_s=20, labels=("emulator", "injection"))
async def packets(t):
    await t.reach("before_receive")
    with restored(t):
        first = await deliver(t, PACKET_A)
        t.check("первый пакет принят", [first, t.read("stats.last_type"), t.read("stats.last_sum")], [1, 0x21, 12])
        second = await deliver(t, PACKET_B)
        got = observe(t, "buffer-call", [PACKET_A, PACKET_B], [first, second])
        order = [got["sequence"], got["last_type"], got["last_sum"], got["accepted"]]
        t.check("порядок пакетов", order, [2, 0x22, 9, 2])
        await next_packet(t, 3, 3)


# Отказный пакет не меняет результат обработки; следующий пакет принимается.
@case("HW_BUFFER_REJECT", timeout_s=20, labels=("emulator", "injection"))
async def reject(t):
    await t.reach("before_receive")
    with restored(t):
        bad = await deliver(t, PACKET_BAD)
        t.check("искажённый пакет отвергнут", [bad, t.read("stats.sequence"), t.read("stats.last_type")], [0, 0, 0])
        good = await deliver(t, PACKET_A)
        got = observe(t, "buffer-call", [PACKET_BAD, PACKET_A], [bad, good])
        counters = [got["accepted"], got["rejected"], got["sequence"], got["last_type"]]
        t.check("вход после отказа", counters, [1, 1, 1, 0x21])
        await next_packet(t, 2, 3)


# Вложенный вызов во время штатной обработки отвергается и не портит текущий пакет.
@case("HW_BUFFER_REENTRY", timeout_s=20, labels=("emulator", "injection"))
async def reentry(t):
    await t.reach("before_receive")
    with restored(t):
        await t.reach("inside_handler")
        t.check("штатная обработка идёт", [t.read("stats.busy"), t.read("stats.entries")], [1, 1])
        nested = await deliver(t, PACKET_A)
        got = observe(t, "buffer-call-reentry", [PACKET_A], [nested])
        t.check("вложенный вход отвергнут", [nested, got["rejected"], got["sequence"], got["busy"]], [0, 1, 0, 1])
        await next_packet(t, 1, 2)
        t.check("отказ учтён один раз", t.read("stats.rejected"), 1)


# Pointer длиннее массива из DWARF отклоняется до вызова: обработчик не исполняется.
@case("HW_BUFFER_BOUNDS", timeout_s=20, labels=("emulator", "injection"))
async def bounds(t):
    await t.reach("before_receive")
    with restored(t):
        put(t, PACKET_A)
        with t.refused("argument_range", name="Pointer за границей массива", stage="validation", effect="none"):
            await t.call("handle_packet", Pointer("inject_buf", count=17), 17, signature=SIGNATURE, timeout=2)
        got = observe(t, "buffer-call-refused", [PACKET_A], [])
        t.check("обработчик не вызывался", [got["entries"], got["accepted"], got["rejected"]], [0, 0, 0])
        await next_packet(t, 1, 1)


# Намеренный FAIL: запись в буфер без вызова обработчика не является потреблением.
@case("HW_BUFFER_UNCONSUMED", timeout_s=20, labels=("emulator", "injection"))
async def unconsumed(t):
    await t.reach("before_receive")
    with restored(t):
        put(t, PACKET_A)
        await t.reach("after_processing")
        got = observe(t, "buffer-write-only", [PACKET_A], [])
        t.check("пакет опыта потреблён", got["last_type"], 0x21)


# Намеренный ERROR после записи: finally обязан вернуть всю секцию опыта.
@case("HW_BUFFER_EXCEPTION", timeout_s=20, labels=("emulator", "injection"))
async def exception(t):
    await t.reach("before_receive")
    with restored(t):
        put(t, PACKET_A)
        t.record("interruption", {"stage": "before-call", "bytes": len(PACKET_A)})
        raise RuntimeError("buffer-consumption: intentional exception before call")
