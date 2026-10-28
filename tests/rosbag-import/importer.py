"""Офлайн-адаптер: ROS1 bag v2 → нейтральный набор каналов и выборок.

Адаптер только переводит формат: топики становятся каналами с объявленными
единицами, время записи сохраняется с явным источником часов. Опоры времени,
сегменты и сравнение с отладчиком — утверждения анализа, а не импорта.
"""
import hashlib
import json

import rosbag1

ADAPTER = "ros1-bag-v2"
RECORD_CLOCK = {"name": "ros1_record_time", "epoch": "unix", "resolution_ns": 1,
                "meaning": "время приёма сообщения хостом записи; не часы МК и не момент чтения GDB"}


def import_bag(blob, channels):
    """(import.json, строки samples.jsonl). channels: topic → {"name", "unit"}."""
    doc = {"schema": 1, "adapter": ADAPTER, "status": "INVALID", "reason": None,
           "source": {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)},
           "clock": {"record_time": RECORD_CLOCK}, "channels": []}
    try:
        bag = rosbag1.read(blob)
    except rosbag1.BagError as error:
        doc.update(reason=error.reason, detail=error.detail)
        return doc, []
    names = {}
    # Объявленные топики получают имя и единицы; остальные сохраняются без единиц.
    for info in sorted(bag["connections"].values(), key=lambda c: c["topic"]):
        declared = channels.get(info["topic"], {})
        name = declared.get("name", info["topic"])
        if name in names.values():
            doc.update(reason="channel_name", detail=f"duplicate {name}")
            return doc, []
        names[info["conn"]] = name
        doc["channels"].append({"name": name, "topic": info["topic"], "type": info["type"], "md5": info["md5"],
                                "kind": info["kind"], "decoded": info["kind"] is not None,
                                "unit": declared.get("unit"), "count": 0, "nonfinite": 0})
    by_name = {c["name"]: c for c in doc["channels"]}
    lines, seq = [], {}
    for message in bag["messages"]:
        channel = by_name[names[message["conn"]]]
        number = seq.get(channel["name"], 0)
        seq[channel["name"]] = number + 1
        channel["count"] += 1
        row = {"channel": channel["name"], "seq": number, "t_ns": message["time_ns"], "value": message["value"]}
        if message.get("nonfinite"):
            channel["nonfinite"] += 1
            row["value"], row["nonfinite"] = None, repr(message["value"])
        lines.append(json.dumps(row, ensure_ascii=False, allow_nan=False))
    times = [m["time_ns"] for m in bag["messages"]]
    doc["bag"] = {"chunks": bag["chunks"], "compression": bag["compression"],
                  "connections": len(bag["connections"]), "messages": len(times),
                  "start_ns": min(times) if times else None, "end_ns": max(times) if times else None}
    doc["status"] = "COMPLETE"
    return doc, lines
