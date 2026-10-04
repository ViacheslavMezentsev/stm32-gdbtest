"""
RU: Вычисление выражений: приведение типов и отказы.
EN: Expression evaluation: type conversion and refusals.
"""
from stm32_gdbtest import ApiError, case


# Arithmetic runs in the debugger and the requested type is applied to the result.
@case("HW_CI_EVALUATE", timeout_s=45, labels=("api", "evaluate"), contracts=("ci_app_api",))
def evaluate_expressions(target):
    target.reach("app_loop")

    # Without as_type the declared type is kept.
    target.check("integer arithmetic", target.evaluate("1 + 1"), 2)
    target.check("the result keeps the declared int type",
                 type(target.evaluate("2 + 3")) is int, True)

    # as_type applies the requested conversion.
    target.check("float conversion", target.evaluate("2 + 3", as_type=float), 5.0)
    target.check("the converted result is a float",
                 type(target.evaluate("2 + 3", as_type=float)) is float, True)
    target.check("bool conversion of a nonzero value", target.evaluate("2 + 3", as_type=bool), True)
    target.check("bool conversion of zero", target.evaluate("1 - 1", as_type=bool), False)
    target.check("the converted result is a bool",
                 type(target.evaluate("1 - 1", as_type=bool)) is bool, True)

    # Conversion truncates towards zero, as C does.
    target.check("int conversion truncates", target.evaluate("(float)7 / 2", as_type=int), 3)
    target.check("a type name is accepted", target.evaluate("2 + 3", as_type="float"), 5.0)

    # The debugger reports its own failures and the API keeps them structured.
    try:
        target.evaluate("api030_no_such_symbol")
    except ApiError as error:
        target.check("failed expression code", error.details["code"], "command_failed")
        target.check("failed expression keeps the cause", error.__cause__ is not None, True)
    else:
        target.check("an unknown symbol must fail", False, True)
    for expression in ("", "   ", "1 +"):
        try:
            target.evaluate(expression)
        except ApiError as error:
            target.check("refused expression code", error.details["code"],
                         "invalid_expression" if not expression.strip() else "command_failed")
        else:
            target.check("an invalid expression must be refused", False, True)
    try:
        target.evaluate("1 + 1", as_type=str)
    except ApiError as error:
        target.check("unsupported as_type code", error.details["code"], "unsupported_type")
    else:
        target.check("an unsupported as_type must be refused", False, True)
