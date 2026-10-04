"""
RU: Алиас декоратора @test: сценарий объявляется тем же способом, что и @case.
EN: The @test alias: a scenario is declared exactly as with @case.
"""
from stm32_gdbtest import test


# Both names declare a scenario and deliver the same Target.
@test("HW_CI_TEST_ALIAS", timeout_s=45, labels=("api", "test"), contracts=("ci_app_api",))
def test_alias(target):
    target.reach("app_loop")

    # Running at all proves the harness accepted the alias instead of skipping the function.
    target.check("the alias declared a runnable scenario", callable(test), True)
    target.check("the scenario has its own id", target.report["id"], "HW_CI_TEST_ALIAS")
    target.check("the scenario sees the target", type(target).__name__, "Target")
    target.check("the target is halted where the scenario stopped",
                 target.frames(limit=1)["frames"][0]["name"], "app_loop")

    # The alias and the original name are interchangeable: both return the function unchanged.
    def scenario(candidate):
        return candidate

    target.check("the alias returns the function unchanged",
                 test("HW_CI_TEST_ALIAS")(scenario) is scenario, True)
