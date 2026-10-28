"""Синтетическая ROS1 bag v2 для CI: нейтральные каналы, заданные заранее времена и значения.

Файл строится побайтно по формату bag v2 (заголовок, чанк, index data, connection,
chunk info). Варианты портят ровно одно свойство записи или её окружения.
"""
import bz2
import struct

T0 = 1_700_000_000_000_000_000
PERIOD_NS = 200_000_000
LATENCY_NS = 10_000_000
COUNT = 50
UPTIME_START_S = 2
DEFINITIONS = {"std_msgs/UInt32": ("304a39449588c7f8ce2df6e8001c5fce", "uint32 data"),
               "std_msgs/Float32": ("73fcbf46b49191e672908e50842a83d4", "float32 data"),
               "std_msgs/Float64": ("fdb28210bfa9d7c91146260178d9a584", "float64 data"),
               "std_msgs/Bool": ("8b94c1b53db61fb6aed406028ad6332a", "bool data"),
               "std_msgs/String": ("992ce8a1687cec8c8bd883ec73ca41d1", "string data\n")}
TOPICS = (("/demo/sys/uptime_s", "std_msgs/UInt32"), ("/demo/sensor/level_v", "std_msgs/Float32"),
          ("/demo/sensor/reference_v", "std_msgs/Float32"), ("/demo/state/mode", "std_msgs/String"),
          ("/demo/state/ready", "std_msgs/Bool"))


def field(name, value):
    blob = name.encode() + b"=" + value
    return struct.pack("<I", len(blob)) + blob


def record(header, data=b""):
    blob = b"".join(field(k, v) for k, v in header.items())
    return struct.pack("<I", len(blob)) + blob + struct.pack("<I", len(data)) + data


def stamp(time_ns):
    return struct.pack("<II", time_ns // 1_000_000_000, time_ns % 1_000_000_000)


def level(mcu_ms):
    """Ступени по 3 с, переход на полусекунде: 1.25 В до 3.5 с, затем 2.5 В, 3.75 В..."""
    return 1.25 * (1 + max(0, (mcu_ms - 500) // 3000))


def encode(kind, value):
    if kind == "std_msgs/UInt32":
        return struct.pack("<I", value)
    if kind == "std_msgs/Float32":
        return struct.pack("<f", value)
    if kind == "std_msgs/Float64":
        return struct.pack("<d", value)
    if kind == "std_msgs/Bool":
        return struct.pack("<B", int(value))
    data = value.encode()
    return struct.pack("<I", len(data)) + data


def stream(variant):
    """Список (topic, receive_ns, value): публикация по МК-часам + постоянная задержка."""
    rows = []
    for index in range(COUNT):
        mcu_ms = UPTIME_START_S * 1000 + index * PERIOD_NS // 1_000_000
        receive = T0 + index * PERIOD_NS + LATENCY_NS
        if variant == "reset" and index >= 25:
            # Сброс МК после 25-й публикации: uptime начинается заново с 2 с.
            mcu_ms = UPTIME_START_S * 1000 + (index - 25) * PERIOD_NS // 1_000_000
        if variant == "halted" and 18 <= index < 33:
            # Остановка отладчиком (публикаций нет), затем сброс при завершении сеанса.
            continue
        if variant == "halted" and index >= 33:
            mcu_ms = UPTIME_START_S * 1000 + (index - 33) * PERIOD_NS // 1_000_000
        values = {"/demo/sys/uptime_s": mcu_ms // 1000, "/demo/sensor/level_v": level(mcu_ms),
                  "/demo/sensor/reference_v": 1.0, "/demo/state/mode": "IDLE", "/demo/state/ready": True}
        if variant == "nan" and index == 16:
            values["/demo/sensor/level_v"] = float("nan")
        for offset, (topic, _) in enumerate(TOPICS):
            rows.append((topic, receive + offset * 1000, values[topic]))
    if variant == "clock_shift":
        rows = [(topic, time + 3600 * 1_000_000_000, value) for topic, time, value in rows]
    return rows


def build(variant="normal"):
    """Байты bag v2 для варианта; повреждения вносятся после сборки корректной записи."""
    topics = list(TOPICS)
    if variant == "wrong_type":
        topics[1] = ("/demo/sensor/level_v", "std_msgs/Float64")
    if variant == "wrong_channel":
        topics[1] = ("/demo/sensor/level_mv", "std_msgs/Float32")
    if variant == "no_anchor":
        topics = topics[1:]
    names = {topic: number for number, (topic, _) in enumerate(topics)}
    kinds = dict(topics)
    rename = {"/demo/sensor/level_v": "/demo/sensor/level_mv"} if variant == "wrong_channel" else {}
    chunk, index, conn_blobs = b"", {}, {}
    for number, (topic, kind) in enumerate(topics):
        md5, definition = DEFINITIONS[kind]
        if variant == "bad_md5" and topic == "/demo/sensor/level_v":
            md5 = "0" * 32
        body = b"".join(field(k, v.encode()) for k, v in (("topic", topic), ("type", kind), ("md5sum", md5),
                                                          ("message_definition", definition),
                                                          ("callerid", "/demo_node"), ("latching", "0")))
        conn_blobs[number] = (topic, body)
        chunk += record({"op": b"\x07", "conn": struct.pack("<I", number), "topic": topic.encode()}, body)
    times = []
    for topic, time_ns, value in stream(variant):
        topic = rename.get(topic, topic)
        if topic not in names:
            continue
        number = names[topic]
        index.setdefault(number, []).append((time_ns, len(chunk)))
        times.append(time_ns)
        chunk += record({"op": b"\x02", "conn": struct.pack("<I", number), "time": stamp(time_ns)},
                        encode(kinds[topic], value))
    compression, payload = b"none", chunk
    if variant == "bz2":
        compression, payload = b"bz2", bz2.compress(chunk)
    if variant == "lz4":
        compression = b"lz4"
    head_size = 4096
    body = record({"op": b"\x05", "compression": compression, "size": struct.pack("<I", len(chunk))}, payload)
    counts = {number: len(entries) for number, entries in index.items()}
    for number in sorted(index):
        entries = b"".join(stamp(t) + struct.pack("<I", off) for t, off in index[number])
        body += record({"op": b"\x04", "ver": struct.pack("<I", 1), "conn": struct.pack("<I", number),
                        "count": struct.pack("<I", len(index[number]))}, entries)
    index_pos = len(b"#ROSBAG V2.0\n") + head_size + len(body)
    tail = b""
    for number, (topic, conn_body) in conn_blobs.items():
        tail += record({"op": b"\x07", "conn": struct.pack("<I", number), "topic": topic.encode()}, conn_body)
    if variant == "index_mismatch":
        counts[1] -= 1
    info = b"".join(struct.pack("<II", number, counts[number]) for number in sorted(counts))
    chunk_pos = struct.pack("<Q", len(b"#ROSBAG V2.0\n") + head_size)
    tail += record({"op": b"\x06", "ver": struct.pack("<I", 1), "chunk_pos": chunk_pos,
                    "start_time": stamp(min(times)), "end_time": stamp(max(times)),
                    "count": struct.pack("<I", len(counts))}, info)
    header = {"op": b"\x03", "index_pos": struct.pack("<Q", 0 if variant == "unindexed" else index_pos),
              "conn_count": struct.pack("<I", len(conn_blobs)), "chunk_count": struct.pack("<I", 1)}
    # Заголовок bag дополняется пробелами до 4096 байт, как у rosbag record.
    head = record(header, b" " * (head_size - len(record(header))))
    blob = b"#ROSBAG V2.0\n" + head + body + tail
    if variant == "truncated":
        blob = blob[:len(blob) - 37]
    summary = {"messages": len(times), "start_ns": min(times), "end_ns": max(times), "topics": sorted(names)}
    return blob, summary


def capture(blob, summary, variant="normal"):
    """Нейтральные метаданные захвата: окно record и сводка bag, как у локальной записи."""
    meta = {"schema": 1, "test": "DEMO_TELEMETRY", "status": "PASS",
            "record_start_ns": T0 - 1_000_000_000, "record_stop_ns": T0 + COUNT * PERIOD_NS + 1_000_000_000,
            "bag": dict(summary, size=len(blob))}
    if variant == "wrong_identity":
        meta["test"] = "OTHER_TELEMETRY"
    return meta
