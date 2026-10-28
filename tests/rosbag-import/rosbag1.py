"""Строгий читатель ROS1 bag v2 без сторонних библиотек.

Поддержаны несжатые и bz2-чанки, индекс (connection, chunk info, index data) и
примитивные std_msgs. Любое расхождение записи с индексом, обрыв файла или
неизвестный формат дают BagError с машинной причиной; частичный результат не
возвращается, чтобы неполная запись не выглядела полной.
"""
import bz2
import math
import struct

MAGIC = b"#ROSBAG V2.0\n"
LIMIT = 64 * 1024 * 1024
OP_MESSAGE, OP_HEADER, OP_INDEX, OP_CHUNK, OP_CHUNK_INFO, OP_CONNECTION = 2, 3, 4, 5, 6, 7
# Только определения с известной md5: другой текст определения — другой тип.
TYPES = {
    ("std_msgs/Bool", "8b94c1b53db61fb6aed406028ad6332a"): "bool",
    ("std_msgs/Float32", "73fcbf46b49191e672908e50842a83d4"): "float32",
    ("std_msgs/Float64", "fdb28210bfa9d7c91146260178d9a584"): "float64",
    ("std_msgs/Int32", "da5909fbe378aeaf85e547e830cc1bb7"): "int32",
    ("std_msgs/UInt32", "304a39449588c7f8ce2df6e8001c5fce"): "uint32",
    ("std_msgs/String", "992ce8a1687cec8c8bd883ec73ca41d1"): "string"
}
FORMATS = {"bool": "<B", "float32": "<f", "float64": "<d", "int32": "<i", "uint32": "<I"}


class BagError(ValueError):
    """Запись непригодна; reason — короткий машинный код."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


def u32(value):
    if len(value) != 4:
        raise BagError("header_field", "u32 expected")
    return struct.unpack("<I", value)[0]


def u64(value):
    if len(value) != 8:
        raise BagError("header_field", "u64 expected")
    return struct.unpack("<Q", value)[0]


def stamp(value):
    if len(value) != 8:
        raise BagError("header_field", "time expected")
    sec, nsec = struct.unpack("<II", value)
    if nsec >= 1_000_000_000:
        raise BagError("header_field", "nsec out of range")
    return sec * 1_000_000_000 + nsec


def fields(blob):
    """Поля заголовка name=value; повтор имени — ошибка формата."""
    out, pos = {}, 0
    while pos < len(blob):
        if pos + 4 > len(blob):
            raise BagError("truncated", "header field length")
        size = struct.unpack_from("<I", blob, pos)[0]
        pos += 4
        if size > len(blob) - pos:
            raise BagError("truncated", "header field")
        name, sep, value = blob[pos:pos + size].partition(b"=")
        if not sep or not name:
            raise BagError("header_field", "name=value expected")
        key = name.decode("ascii", "strict")
        if key in out:
            raise BagError("header_field", f"duplicate {key}")
        out[key] = value
        pos += size
    return out


def records(buf, pos, end):
    """Последовательность (header, data, offset) в пределах [pos, end)."""
    while pos < end:
        start = pos
        if pos + 4 > end:
            raise BagError("truncated", f"record at {start}")
        header_len = struct.unpack_from("<I", buf, pos)[0]
        pos += 4
        if header_len > end - pos:
            raise BagError("truncated", f"header at {start}")
        header = fields(buf[pos:pos + header_len])
        pos += header_len
        if pos + 4 > end:
            raise BagError("truncated", f"data length at {start}")
        data_len = struct.unpack_from("<I", buf, pos)[0]
        pos += 4
        if data_len > end - pos:
            raise BagError("truncated", f"data at {start}")
        if "op" not in header or len(header["op"]) != 1:
            raise BagError("header_field", f"op at {start}")
        yield header, buf[pos:pos + data_len], start
        pos += data_len


def decode(kind, data):
    """Значение примитивного std_msgs; лишние байты — ошибка сериализации."""
    if kind == "string":
        if len(data) < 4 or struct.unpack_from("<I", data)[0] != len(data) - 4:
            raise BagError("message_size", "string")
        return data[4:].decode("utf-8", "strict")
    fmt = FORMATS[kind]
    if len(data) != struct.calcsize(fmt):
        raise BagError("message_size", kind)
    value = struct.unpack(fmt, data)[0]
    if kind == "bool":
        if value not in (0, 1):
            raise BagError("message_value", "bool")
        return bool(value)
    return value


def connection(header, data):
    conn = u32(header.get("conn", b""))
    body = fields(data)
    topic = header.get("topic", b"").decode("utf-8")
    try:
        info = {"conn": conn, "topic": topic, "type": body["type"].decode("utf-8"),
                "md5": body["md5sum"].decode("ascii"),
                "definition": body.get("message_definition", b"").decode("utf-8"),
                "callerid": body.get("callerid", b"").decode("utf-8"),
                "latching": body.get("latching", b"0") == b"1"}
    except KeyError as error:
        raise BagError("connection", f"missing {error}") from None
    if body.get("topic", header.get("topic")) != header.get("topic"):
        raise BagError("connection", "topic differs")
    info["kind"] = TYPES.get((info["type"], info["md5"]))
    return info


def unpack_chunk(header, data):
    compression = header.get("compression", b"").decode("ascii", "replace")
    size = u32(header.get("size", b""))
    if size > LIMIT:
        raise BagError("too_large", "chunk")
    if compression == "none":
        raw = data
    elif compression == "bz2":
        try:
            raw = bz2.BZ2Decompressor().decompress(data, max_length=size + 1)
        except (OSError, ValueError) as error:
            raise BagError("chunk_decompress", str(error)) from None
    else:
        raise BagError("unsupported_compression", compression)
    if len(raw) != size:
        raise BagError("chunk_size", f"{len(raw)} != {size}")
    return compression, raw


def read(blob):
    """Полное чтение и сверка с индексом. Возвращает dict с connections/messages."""
    if len(blob) > LIMIT:
        raise BagError("too_large", "file")
    if not blob.startswith(MAGIC):
        raise BagError("not_bag_v2", "magic")
    items = records(blob, len(MAGIC), len(blob))
    try:
        header, _, _ = next(items)
    except StopIteration:
        raise BagError("truncated", "bag header") from None
    if header["op"][0] != OP_HEADER:
        raise BagError("not_bag_v2", "first record")
    index_pos = u64(header.get("index_pos", b""))
    conn_count = u32(header.get("conn_count", b""))
    chunk_count = u32(header.get("chunk_count", b""))
    if index_pos == 0:
        raise BagError("unindexed", "index_pos=0")
    if index_pos > len(blob):
        raise BagError("truncated", "index_pos beyond file")
    conns, messages, chunks, infos, indexes = {}, [], [], [], {}
    index_conns = {}
    for header, data, offset in items:
        op = header["op"][0]
        if op == OP_CHUNK:
            if offset >= index_pos:
                raise BagError("layout", "chunk after index")
            compression, raw = unpack_chunk(header, data)
            chunk = {"pos": offset, "compression": compression, "counts": {}, "times": []}
            chunks.append(chunk)
            # Внутри чанка разрешены только connection и сообщения.
            for inner, body, inner_offset in records(raw, 0, len(raw)):
                kind = inner["op"][0]
                if kind == OP_CONNECTION:
                    info = connection(inner, body)
                    if info["conn"] in conns and conns[info["conn"]] != info:
                        raise BagError("connection", "redefined")
                    conns[info["conn"]] = info
                elif kind == OP_MESSAGE:
                    conn = u32(inner.get("conn", b""))
                    if conn not in conns:
                        raise BagError("connection", f"message before connection {conn}")
                    time_ns = stamp(inner.get("time", b""))
                    messages.append({"conn": conn, "time_ns": time_ns, "data": body,
                                     "chunk": len(chunks) - 1, "offset": inner_offset})
                    chunk["counts"][conn] = chunk["counts"].get(conn, 0) + 1
                    chunk["times"].append(time_ns)
                else:
                    raise BagError("layout", f"op {kind} inside chunk")
        elif op == OP_INDEX:
            if u32(header.get("ver", b"")) != 1:
                raise BagError("index_mismatch", "index version")
            conn, count = u32(header.get("conn", b"")), u32(header.get("count", b""))
            if len(data) != 12 * count:
                raise BagError("index_mismatch", "index size")
            entries = [(stamp(data[i:i + 8]), struct.unpack_from("<I", data, i + 8)[0])
                       for i in range(0, len(data), 12)]
            indexes.setdefault(len(chunks) - 1, {}).setdefault(conn, []).extend(entries)
        elif op == OP_CONNECTION:
            if offset < index_pos:
                raise BagError("layout", "connection outside index")
            info = connection(header, data)
            index_conns[info["conn"]] = info
        elif op == OP_CHUNK_INFO:
            if u32(header.get("ver", b"")) != 1:
                raise BagError("index_mismatch", "chunk info version")
            count = u32(header.get("count", b""))
            if len(data) != 8 * count:
                raise BagError("index_mismatch", "chunk info size")
            counts = dict(struct.unpack_from("<II", data, i) for i in range(0, len(data), 8))
            infos.append({"pos": u64(header.get("chunk_pos", b"")), "start": stamp(header.get("start_time", b"")),
                          "end": stamp(header.get("end_time", b"")), "counts": counts})
        elif op == OP_HEADER:
            raise BagError("layout", "second bag header")
        else:
            raise BagError("layout", f"unknown op {op}")
    # Сверка: заголовок, connection индекса, chunk info и index data против содержимого.
    if len(chunks) != chunk_count or len(infos) != chunk_count:
        raise BagError("index_mismatch", "chunk count")
    if len(conns) != conn_count or index_conns != conns:
        raise BagError("index_mismatch", "connections")
    for number, (chunk, info) in enumerate(zip(chunks, infos)):
        if info["pos"] != chunk["pos"] or info["counts"] != chunk["counts"]:
            raise BagError("index_mismatch", f"chunk {number} counts")
        if chunk["times"] and (info["start"] != min(chunk["times"]) or info["end"] != max(chunk["times"])):
            raise BagError("index_mismatch", f"chunk {number} times")
        listed = indexes.get(number, {})
        actual = {}
        for message in messages:
            if message["chunk"] == number:
                actual.setdefault(message["conn"], []).append((message["time_ns"], message["offset"]))
        if {k: sorted(v) for k, v in listed.items()} != {k: sorted(v) for k, v in actual.items()}:
            raise BagError("index_mismatch", f"chunk {number} index data")
    for message in messages:
        kind = conns[message["conn"]]["kind"]
        message["value"] = decode(kind, message["data"]) if kind else None
        if isinstance(message["value"], float) and not math.isfinite(message["value"]):
            message["nonfinite"] = True
    messages.sort(key=lambda m: (m["time_ns"], m["chunk"], m["offset"]))
    return {"connections": conns, "messages": messages,
            "compression": sorted({c["compression"] for c in chunks}), "chunks": len(chunks)}
