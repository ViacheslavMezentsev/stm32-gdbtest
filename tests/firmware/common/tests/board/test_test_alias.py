"""
RU: Алиас декоратора @test: сценарий объявляется тем же способом, что и @case.
EN: The @test alias: a scenario is declared exactly as with @case.
"""
from stm32_gdbtest import test


# Both names declare a scenario and deliver the same Target.
@test("HW_CI_TEST_ALIAS", timeout_s=45, labels=("api", "test"), contracts=("ci_app_api",))
def test_alias(t):
    t.reach("app_loop")

    # Running at all proves the harness accepted the alias instead of skipping the function.
    t.check("the alias declared a runnable scenario", callable(test), True)
    t.check("the scenario has its own id", t.report["id"], "HW_CI_TEST_ALIAS")
    t.check("the scenario sees the target", type(t).__name__, "Target")
    t.check("the target is halted where the scenario stopped", t.frames(limit=1)["frames"][0]["name"], "app_loop")

    # The alias and the original name are interchangeable: both return the function unchanged.
    def scenario(candidate):
        return candidate

    t.check("the alias returns the function unchanged", test("HW_CI_TEST_ALIAS")(scenario) is scenario)
