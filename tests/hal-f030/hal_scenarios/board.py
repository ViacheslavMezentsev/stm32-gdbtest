"""
RU: Общие HAL-проверки запуска, тактирования и GPIO платы.
EN: Shared HAL startup, clock and board GPIO checks.
"""

# HSI is the system clock of the board (RM0360: 8 MHz nominal).
HSI_HZ = 8_000_000
# Application loop period of the HAL fixture (HAL_Delay in platform.c), in milliseconds.
LOOP_DELAY_MS = 500
# HAL tick counter uwTick is a uint32_t and wraps around.
U32_MASK = 0xFFFFFFFF


# Verify that startup reaches the application loop.
def boot(t, expected):
    t.reach("loop")


# Verify clock selection, bus dividers and the system tick configuration.
def clock(t, expected):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    t.reach("platform_adc_start")

    # Check the nominal core clock before the profile-specific clock checks.
    t.check("SystemCoreClock", t.read("SystemCoreClock"), HSI_HZ)

    # Evaluate each profile expectation in the peripheral source context.
    t.check(expected["clock"])


# Verify the board LED pin configuration and initial output state.
def gpio(t, expected):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    t.reach("platform_adc_start")

    # Evaluate each profile expectation in the peripheral source context.
    t.check(expected["gpio"])


# Observe consecutive LED transitions and their firmware timing.
def blink(t, expected):
    t.reach("platform_adc_start")
    tick = t.read("uwTick")

    # Observe alternating output levels and check the elapsed firmware ticks.
    for level in (1 - expected["led_initial"], expected["led_initial"]):
        t.reach("platform_adc_start")

        # Check that the output alternates between the expected levels.
        t.check("LED pin toggled", int(t.evaluate(expected["led_level"])), level)

        next_tick = t.read("uwTick")
        delta = (next_tick - tick) & U32_MASK
        t.report.setdefault("loop_tick_deltas_ms", []).append(delta)

        # Verify the HAL delay of the loop.
        t.check(f"HAL delay >= {LOOP_DELAY_MS} ms", delta >= LOOP_DELAY_MS)

        tick = next_tick
