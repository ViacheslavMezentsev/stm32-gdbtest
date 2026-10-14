"""Run inside GDB on a fresh, owned Renode instance; no physical target."""
import json

import gdb


# Evaluate scalars on GDB's main thread; calls in expressions execute target code.
def value(expression):
    return int(gdb.parse_and_eval(expression))


# Read the entire backing page independently of the C++ cache.
def storage():
    return bytes(gdb.selected_inferior().read_memory(0x0800F800, 2048))


# Record the limited register invariants; this is not a complete CPU context check.
def registers():
    frame = gdb.newest_frame()
    return {name: int(frame.read_register(name)) for name in ("pc", "sp")}


# Read a word from the teaching peripheral, bypassing the firmware adapter.
def read_register(offset):
    data = gdb.selected_inferior().read_memory(0x40022000 + offset, 4)
    return int.from_bytes(bytes(data), "little")


# Write a word through GDB, not through a running firmware driver.
def write_register(offset, number):
    gdb.selected_inferior().write_memory(0x40022000 + offset, number.to_bytes(4, "little"))


# Check the shared suite and then call methods of the already constructed object.
def check_calls():
    names = ("checks", "failure_line", "stores_seen", "programs_seen", "guard_ok")
    result = {name: value(name) for name in names}
    print("CACHE_RESULT=" + json.dumps(result))
    expected_stores = 2 if value("$negative_control") else 1
    assert result == dict(checks=24, failure_line=0, stores_seen=expected_stores, programs_seen=256, guard_ok=1)
    expected = bytearray(2048)
    expected[3], expected[-1] = 0x42, 0x17
    assert storage() == bytes(expected)

    # The caller owns the live object, adapter and argument storage.
    original = registers()
    owner = gdb.newest_frame().older()
    assert owner.name() == "reset_handler"
    owner.select()
    gdb.execute("set $cache = &interactive")
    gdb.execute("set $input = &call_byte")
    gdb.execute("set $adapter = &adapter")

    # A cache write must not reach the backing storage until commit.
    baseline = storage()
    assert value("$cache->dirty()") == 0
    assert value("$cache->write(5, $input, 1)") == 1
    assert value("$cache->dirty()") == 1 and storage() == baseline
    assert value("$adapter->stores") == 1
    assert value("$cache->read(5, $input, 1)") == 1 and value("*$input") == 0x66
    assert value("$cache->write(2048, $input, 1)") == 0 and storage() == baseline

    # Check exact persistence and idempotence, not only the returned bool.
    assert value("$cache->commit()") == 1
    expected[5] = 0x66
    assert storage() == bytes(expected) and value("$adapter->stores") == 2
    assert value("$cache->dirty()") == 0
    assert value("$cache->commit()") == 1 and value("$adapter->stores") == 2
    returned = registers()
    print("CALL_REGISTERS=" + json.dumps(dict(before=original, after=returned)))
    assert returned == original

    # Wrong size is rejected before the adapter reads the small input buffer.
    before_store, before_count = storage(), value("$adapter->stores")
    assert value("$adapter->store($input, 2047)") == 0
    assert storage() == before_store and value("$adapter->stores") == before_count
    print("INVALID_SIZE_REFUSED")
    print("CPP_CALLS_PASS")


# Deliberately alter model state after the C++ checks; do not resume the application.
def check_model():
    inferior = gdb.selected_inferior()
    lock = 0x80000000
    write_register(0x14, lock)
    write_register(8, 0x12345678)
    write_register(8, 0xCDEF89AB)
    assert read_register(0x14) & lock
    write_register(8, 0x45670123)
    write_register(8, 0xCDEF89AB)
    assert not read_register(0x14) & lock
    write_register(0x10, 1)
    assert not read_register(0x10) & 1

    # This intentionally incomplete model permits a CR write to bypass LOCK.
    write_register(0x14, lock)
    assert read_register(0x14) & lock
    write_register(0x14, (31 << 3) | 2 | 0x10000)
    erased = storage() == bytes([255]) * 2048
    print("MODEL_LOCK_BYPASS=" + json.dumps(dict(erased_without_keys=erased, cr=read_register(0x14))))
    assert erased, "Model behavior changed: revisit the limitation, do not assume protection"
    assert bytes(inferior.read_memory(0x0800F7FC, 4)) == bytes([0x78, 0x56, 0x34, 0x12])
    write_register(0x10, 1)
    assert not read_register(0x10) & 1

    # Exercise the bank boundary and final page with independent adjacent guards.
    boundaries = []
    for page in (127, 128, 255):
        address = 0x08000000 + page * 2048
        left, right = bytes([0x12, 0x34, 0x56, 0x78]), bytes([0x87, 0x65, 0x43, 0x21])
        inferior.write_memory(address - 4, left)
        inferior.write_memory(address, bytes([0xA5]) * 2048)
        inferior.write_memory(address + 2048, right)
        write_register(0x14, lock)
        write_register(8, 0x45670123)
        write_register(8, 0xCDEF89AB)
        assert not read_register(0x14) & lock
        write_register(0x10, 1)
        control = ((page % 128) << 3) | (0x800 if page >= 128 else 0) | 2 | 0x10000
        write_register(0x14, control)
        assert bytes(inferior.read_memory(address, 2048)) == bytes([255]) * 2048
        assert bytes(inferior.read_memory(address - 4, 4)) == left
        assert bytes(inferior.read_memory(address + 2048, 4)) == right
        assert read_register(0x10) & 1 and not read_register(0x14) & 0x10000
        boundaries.append(dict(page=page, address=address, neighbors_preserved=True))
    print("PAGE_BOUNDARIES=" + json.dumps(boundaries))

    # PG reports completion without a payload: EOP alone cannot establish a write.
    address = 0x0807F800
    inferior.write_memory(address, bytes([0xA5]) * 2048)
    write_register(0x10, 1)
    write_register(0x14, 1)
    assert read_register(0x10) & 1
    assert bytes(inferior.read_memory(address, 2048)) == bytes([0xA5]) * 2048
    print("MODEL_PROGRAM_STUB=" + json.dumps(dict(eop_without_payload=True, data_unchanged=True)))


if not __debug__:
    raise RuntimeError("This example requires Python assertions enabled")

try:
    check_calls()
    check_model()
    print("ELF_CHECK_PASS")
except AssertionError:
    print("SCENARIO_ASSERTION_FAILURE")
    raise
