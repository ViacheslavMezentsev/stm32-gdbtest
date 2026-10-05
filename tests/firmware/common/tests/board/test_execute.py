"""
RU: Команды отладчика через execute: вывод, журнал, усечение и отказы.
EN: Debugger commands through execute: output, journal, truncation and refusals.
"""
from hashlib import sha256

from stm32_gdbtest import case


# Longer than the default output limit of api.toml (execute.output_limit_chars = 2048).
LONG_OUTPUT = "X" * 3000


# The result is the debugger text; the journal keeps the length and the truncation flag.
@case("HW_CI_EXECUTE", timeout_s=90, labels=("api", "execute", "invoke"), contracts=("ci_app_api",))
def execute_commands(t):
    t.reach("app_loop")

    # A real debugger command returns its text and is journalled.
    text = t.execute("info registers pc sp")
    t.check("execute returns text", type(text) is str)
    t.check("execute returns a non-empty result", len(text) > 0)
    entry = t.report["executions"][-1]
    t.check("journal keeps the command", entry["command"], "info registers pc sp")
    t.check("journal marks the result", entry["result"], "ok")
    t.check("journal keeps the length", entry["output_length"], len(text))
    t.check("a short result is not truncated", entry["truncated"], False)
    t.check("journal keeps the configured limit", entry["limit"], 2048)

    # Refusals happen before the debugger is touched and leave no journal entry behind.
    entries = len(t.report["executions"])

    # Empty and multi-line commands.
    for command in ("", "   ", "info\nregisters"):
        with t.refused("invalid_command", stage="validation", name=f"invalid command {command!r} is refused"):
            t.execute(command)
    t.check("refusals are not journalled", len(t.report["executions"]), entries)

    # An output above the limit is reported as truncated with the hash of the full text.
    print("API030_V34_CHECKPOINT=long_output", flush=True)
    long_text = t.execute("echo " + LONG_OUTPUT)
    long_entry = t.report["executions"][-1]
    t.check("the full text is returned", len(long_text) >= len(LONG_OUTPUT))
    t.check("a long result is truncated", long_entry["truncated"])
    t.check("the journal keeps the full length", long_entry["output_length"], len(long_text))
    t.check("the journal hashes the full text", long_entry["output_sha256"],
            sha256(long_text.encode("utf-8")).hexdigest())

    # A failing debugger command is reported with its cause and is not repeated.
    print("API030_V34_CHECKPOINT=failing_command", flush=True)
    with t.refused("command_failed", name="an unknown command fails") as failure:
        t.execute("api030-no-such-command")
    t.check("failed command keeps the cause", failure.error.__cause__ is not None)
    t.check("failed command is journalled", t.report["executions"][-1]["result"], "failed")
