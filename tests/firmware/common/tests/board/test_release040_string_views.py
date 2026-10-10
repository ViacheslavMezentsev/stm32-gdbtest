"""
RU: Ограниченные и неизвестные границы строк MCU: чтение представлений без изменения памяти.
EN: Bounded and unknown MCU string extents: read views without modifying target memory.
"""
from stm32_gdbtest import case


# Compare bounded array, unsized array and pointer views of the same stopped firmware data.
@case("HW_CI_040_STRING_VIEWS", timeout_s=45, labels=("api040", "strings"), contracts=("ci_app_api",))
def string_views(t):
    t.reach("app_loop")
    address = t.evaluate("&app_version_ram[0]", as_type=int)
    size = t.evaluate("sizeof(app_version_ram)")
    before = t.memory(address, size)

    # A three-byte char array has no terminator: its known bound prevents an over-read.
    bounded = t.evaluate("*(volatile char (*)[3])app_version_ram", as_type=str)
    unsized = t.evaluate("*(volatile char (*)[])app_version_ram", as_type=str)
    pointer = t.evaluate("(volatile char *)app_version_ram", as_type=str)
    t.check("bounded prefix", bounded, "v1.")
    t.check("unknown bound reads the complete string", unsized, "v1.2.0-ci")
    t.check("pointer agrees with unsized array", pointer, unsized)
    t.check("views leave memory unchanged", t.memory(address, size), before)
    t.record("string.views", {"bounded": bounded, "unsized": unsized, "pointer": pointer, "size": size})
