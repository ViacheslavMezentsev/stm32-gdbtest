"""
RU: Строки прошивки: функции GDB в таблице check(rows) и evaluate(..., as_type=str) в Python.
EN: Firmware strings: GDB functions in a check(rows) table and evaluate(..., as_type=str) in Python.
"""
from stm32_gdbtest import case, matches

# The identification strings of the fixture firmware (src/app.c), stated independently here.
VERSION = "v1.2.0-ci"
BOARD = "stm32-gdbtest-ci"


@case("HW_CI_STRINGS", timeout_s=45, labels=("api", "strings"), contracts=("ci_app_api",))
def strings(t):
    # main() has copied the version into RAM before the application loop starts.
    t.reach("app_loop")

    # GDB string functions inside the table: every string cell is a GDB expression, and a two-cell row
    # passes when the expression is true. Python values do not belong in these cells.
    t.check([
        ("version field equals", f'$_streq(app_info.version, "{VERSION}")'),
        ("board pointer equals", f'$_streq(app_info.board, "{BOARD}")'),
        ("version length", "$_strlen(app_info.version)", len(VERSION)),
        ("RAM copy equals the Flash bytes", "$_memeq(app_version_ram, app_info.version, sizeof(app_info.version))"),
        ("version starts with v1.", r'$_regex(app_info.version, "^v1\\.")'),
    ])

    # The same checks in Python: evaluate(..., as_type=str) reads the C string, check compares text.
    version = t.evaluate("app_info.version", as_type=str)
    t.check("version as text", version, VERSION)
    t.check("version length in Python", len(version), len(VERSION))
    t.check("version pattern", version, matches(r"^v1\.\d+\.\d+"))
    t.check("board pointer as text", t.evaluate("app_info.board", as_type=str), BOARD)
    t.check("RAM copy as text", t.evaluate("app_version_ram", as_type=str), version)

    # Raw bytes of both blocks: memory() reads the Flash original and the RAM copy.
    size = t.evaluate("sizeof(app_info.version)")
    flash = t.memory(t.evaluate("&app_info.version[0]", as_type=int), size)
    ram = t.memory(t.evaluate("&app_version_ram[0]", as_type=int), size)
    t.check("RAM copy bytes", ram.hex(), flash.hex())
    t.record("strings", dict(version=version, flash=flash.hex()))
