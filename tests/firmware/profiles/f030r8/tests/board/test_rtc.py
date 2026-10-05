"""
RU: Проверки настройки RTC, повторных прерываний и тайм-аута.
EN: RTC configuration, repeated alarm interrupts and deadline checks.
"""
from stm32_gdbtest import case


# Evaluate table rows in order and stop at the first failed read or check.
def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.evaluate(expression, as_type=int)
        if isinstance(expected, str):
            # An expected cell may be a C expression, an address or an enum, so it is evaluated too.
            expected = target.evaluate(expected, as_type=int)

        # Compare the current row after both expressions have been evaluated.
        target.check(name, actual, expected)


# Verify RTC clock, calendar masks, alarm configuration and interrupt routing.
@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(target):
    target.reach("board_led_toggle")

    # Check register and application state against the expected values.
    _check_values(target, [
        ('LSI ready', '(RCC->CSR & RCC_CSR_LSIRDY) != 0', 1),
        ('LSI RTC clock enabled', 'RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)', 33280),
        ('RTC prescalers', 'RTC->PRER', 127 << 16 | 311),
        ('24-hour Alarm A enabled with IRQ', 'RTC->CR', 4352),
        ('all calendar fields masked', 'RTC->ALRMAR', 2155905152),
        ('subseconds masked', 'RTC->ALRMASSR', 0),
        ('initialization completed', 'RTC->ISR & RTC_ISR_INIT', 0),
        ('shadow synchronized', '(RTC->ISR & RTC_ISR_RSF) != 0', 1),
        ('EXTI17 enabled rising edge', '(EXTI->IMR & EXTI->RTSR) & (1 << 17)', 1 << 17),
        ('EXTI17 falling edge off', 'EXTI->FTSR & (1 << 17)', 0),
        ('RTC NVIC enabled', 'NVIC->ISER[0] & (1 << 2)', 1 << 2),
        ('RTC vector', '(unsigned int)vectors[18] & ~1U', '(unsigned int)RTC_IRQHandler & ~1U'),
        ('no RTC error', 'board_rtc_error', 0)
    ])


# Observe repeated RTC alarm delivery and publication of application events.
@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(target):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    target.reach("RTC_IRQHandler")

    # TECH-002: preserve the CMSIS address/mask before entering HAL-free app.c.
    icsr_address = target.evaluate("&SCB->ICSR", as_type=int)
    active_mask = target.read("SCB_ICSR_VECTACTIVE_Msk")
    before = target.read("board_rtc_events")

    # Observe repeated alarm delivery and confirm one event per interrupt.
    for index in range(2):
        # Check register and application state against the expected values.
        _check_values(target, [
            ('RTC exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 18),
            ('Alarm A pending', '(RTC->ISR & RTC_ISR_ALRAF) != 0', 1),
            ('EXTI17 pending', 'EXTI->PR & (1 << 17)', 1 << 17)
        ])

        target.check("one event per handler", target.read("board_rtc_events"), (before + index) & 0xFFFFFFFF)

        if index == 0:
            target.reach("RTC_IRQHandler")

    target.reach("app_loop")

    # Verify thread resumes.
    target.check("thread resumes", target.read(f"*(unsigned int*){icsr_address} & {active_mask}"), 0)
    target.check("second alarm published", ((target.read("board_rtc_events") - before) & 0xFFFFFFFF) >= 2, True)
    target.check("no RTC error", target.read("board_rtc_error"), 0)


# Make the RTC wait predicate impossible and verify the bounded failure path.
@case("HW_CI_RTC_DEADLINE", timeout_s=90, labels=("rtc", "negative"), contracts=("ci_rtc_macros",))
def rtc_deadline(target):
    # TECH-002: docs/ru/TESTING_TECHNIQUES.md#tech-002 (EN: docs/en/TESTING_TECHNIQUES.md#tech-002).
    # TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
    # Stop at the call that reports the deadline error, then make the wait predicate impossible.
    target.reach("rtc_wait", condition="error == 3")
    target.check("rtc_wait received its error code", target.read("error"), 3)

    # Verify LSI wait mask.
    target.check("LSI wait mask", target.read("mask"), 1 << 1)

    before = target.read("board_ticks_ms")
    backup_address = target.evaluate("&RCC->BDCR", as_type=int)
    backup = target.read(f"*(unsigned int*){backup_address}")

    # Make the ready predicate impossible without touching the oscillator/backup domain.
    target.write("mask", 0)
    target.reach("board_rtc_fault")

    # Check the timeout result without changing backup-domain state.
    target.check("RTC wait timeout reported", target.read("board_rtc_error"), 3)
    target.check("at least 1000 firmware ticks", ((target.read("board_ticks_ms") - before) & 0xFFFFFFFF) >= 1000, True)
    target.check("backup configuration unchanged", target.read(f"*(unsigned int*){backup_address}"), backup)
    target.check("no application loop", target.read("app_state.ticks"), 0)
    target.check("no alarm publication", target.read("board_rtc_events"), 0)

    target.report["injection_scope"] = "rtc_wait mask argument set to zero; not a physical LSI failure"
