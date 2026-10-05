"""
RU: Вычисление выражений: приведение типов и отказы.
EN: Expression evaluation: type conversion and refusals.
"""
from stm32_gdbtest import case, ApiError, case


# Arithmetic runs in the debugger and the requested type is applied to the result.
@case("HW_CI_EVALUATE", timeout_s=45, labels=("api", "evaluate"), contracts=("ci_app_api",))
def evaluate_expressions(t):
    t.reach("app_loop")

    # Without as_type the declared type is kept.
    t.check("integer arithmetic", t.evaluate("1 + 1"), 2)
    t.check("the result keeps the declared int type",
                 type(t.evaluate("2 + 3")) is int)

    # as_type applies the requested conversion.
    t.check("float conversion", t.evaluate("2 + 3", as_type=float), 5.0)
    t.check("the converted result is a float",
                 type(t.evaluate("2 + 3", as_type=float)) is float)
    t.check("bool conversion of a nonzero value", t.evaluate("2 + 3", as_type=bool), True)
    t.check("bool conversion of zero", t.evaluate("1 - 1", as_type=bool), False)
    t.check("the converted result is a bool",
                 type(t.evaluate("1 - 1", as_type=bool)) is bool)

    # Conversion truncates towards zero, as C does.
    t.check("int conversion truncates", t.evaluate("(float)7 / 2", as_type=int), 3)
    t.check("a type name is accepted", t.evaluate("2 + 3", as_type="float"), 5.0)

    # The debugger reports its own failures and the API keeps them structured.
    try:
        t.evaluate("api030_no_such_symbol")
    except ApiError as error:
        t.check("failed expression code", error.details["code"], "command_failed")
        t.check("failed expression keeps the cause", error.__cause__ is not None)
    else:
        t.check("an unknown symbol must fail", False, True)
    for expression in ("", "   ", "1 +"):
        try:
            t.evaluate(expression)
        except ApiError as error:
            t.check("refused expression code", error.details["code"],
                         "invalid_expression" if not expression.strip() else "command_failed")
        else:
            t.check("an invalid expression must be refused", False, True)
    try:
        t.evaluate("1 + 1", as_type=str)
    except ApiError as error:
        t.check("unsupported as_type code", error.details["code"], "unsupported_type")
    else:
        t.check("an unsupported as_type must be refused", False, True)
