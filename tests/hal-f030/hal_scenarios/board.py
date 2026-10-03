"""
RU: Общие HAL-проверки запуска, тактирования и GPIO платы.
EN: Shared HAL startup, clock and board GPIO checks.
"""


# Verify that startup reaches the application loop.
def boot(t, expected):
    t.reach("loop")


# Verify clock selection, bus dividers and the system tick configuration.
def clock(t, expected):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    t.reach("platform_adc_start")

    # Check the nominal core clock before the profile-specific clock checks.
    t.check("SystemCoreClock", t.value("SystemCoreClock"), 8000000)

    # Evaluate each profile expectation in the peripheral source context.
    for name, expression, value in expected["clock"]:
        # Compare the current register expression with the profile expectation.
        t.check(name, t.value(expression), value)


# Verify the board LED pin configuration and initial output state.
def gpio(t, expected):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    t.reach("platform_adc_start")

    # Evaluate each profile expectation in the peripheral source context.
    for name, expression, value in expected["gpio"]:
        # Compare the current register expression with the profile expectation.
        t.check(name, t.value(expression), value)


# Observe consecutive LED transitions and their firmware timing.
def blink(t, expected):
    t.reach("platform_adc_start")
    tick = t.value("uwTick")

    # Observe alternating output levels and check the elapsed firmware ticks.
    for level in (1 - expected["led_initial"], expected["led_initial"]):
        t.reach("platform_adc_start")

        # Check that the output alternates between the expected levels.
        t.check("LED pin toggled", t.value(expected["led_level"]), level)

        next_tick = t.value("uwTick")
        delta = (next_tick - tick) & 0xFFFFFFFF
        t.report.setdefault("loop_tick_deltas_ms", []).append(delta)

        # Verify HAL delay >= 500 ms.
        t.check("HAL delay >= 500 ms", delta >= 500, True)

        tick = next_tick
