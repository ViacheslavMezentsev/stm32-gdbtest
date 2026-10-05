"""
RU: Команды отладчика через execute: вывод, журнал, усечение и отказы.
EN: Debugger commands through execute: output, journal, truncation and refusals.
"""
from hashlib import sha256

from stm32_gdbtest import case, ApiError, case

LONG_OUTPUT = "X" * 3000


# The result is the debugger text; the journal keeps the length and the truncation flag.
@case("HW_CI_EXECUTE", timeout_s=90, labels=("api", "execute", "invoke"), contracts=("ci_app_api",))
def execute_commands(target):
    target.reach("app_loop")

    # A real debugger command returns its text and is journalled.
    text = target.execute("info registers pc sp")
    target.check("execute returns text", type(text) is str, True)
    target.check("execute returns a non-empty result", len(text) > 0, True)
    entry = target.report["executions"][-1]
    target.check("journal keeps the command", entry["command"], "info registers pc sp")
    target.check("journal marks the result", entry["result"], "ok")
    target.check("journal keeps the length", entry["output_length"], len(text))
    target.check("a short result is not truncated", entry["truncated"], False)
    target.check("journal keeps the configured limit", entry["limit"], 2048)

    # Refusals happen before the debugger is touched and leave no journal entry behind.
    entries = len(target.report["executions"])
    for command in ("", "   ", "info\nregisters"):
        try:
            target.execute(command)
        except ApiError as error:
            target.check("refused command code", error.details["code"], "invalid_command")
            target.check("refused command stage", error.details["stage"], "validation")
        else:
            target.check("an invalid command must be refused", False, True)
    target.check("refusals are not journalled", len(target.report["executions"]), entries)

    # An output above the limit is reported as truncated with the hash of the full text.
    print("API030_V34_CHECKPOINT=long_output", flush=True)
    long_text = target.execute("echo " + LONG_OUTPUT)
    long_entry = target.report["executions"][-1]
    target.check("the full text is returned", len(long_text) >= len(LONG_OUTPUT), True)
    target.check("a long result is truncated", long_entry["truncated"], True)
    target.check("the journal keeps the full length", long_entry["output_length"], len(long_text))
    target.check("the journal hashes the full text", long_entry["output_sha256"],
                 sha256(long_text.encode("utf-8")).hexdigest())

    # A failing debugger command is reported with its cause and is not repeated.
    print("API030_V34_CHECKPOINT=failing_command", flush=True)
    try:
        target.execute("api030-no-such-command")
    except ApiError as error:
        target.check("failed command code", error.details["code"], "command_failed")
        target.check("failed command keeps the cause", error.__cause__ is not None, True)
        target.check("failed command is journalled", target.report["executions"][-1]["result"],
                     "failed")
    else:
        target.check("an unknown command must fail", False, True)
