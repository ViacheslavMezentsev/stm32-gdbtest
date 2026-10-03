"""
RU: Проверки настройки RTC, повторных прерываний и тайм-аута.
EN: RTC configuration, repeated alarm interrupts and deadline checks.
"""
from stm32_gdbtest import case


# Evaluate table rows in order and stop at the first failed read or check.
def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)

        # Compare the current row after both expressions have been evaluated.
        target.check(name, actual, expected)


# Verify RTC clock, calendar masks, alarm configuration and interrupt routing.
@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(target):
    target.reach("board_led_toggle")

    # Check register and application state against the expected values.
    _check_values(target, [
        ('LSI ready', '(RCC->CSR & RCC_CSR_LSIRDY) != 0', 1),
        ('LSI RTC clock', 'RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)', 33280),
        ('F1 prescaler', '(RTC->PRLH << 16) | RTC->PRLL', 39999),
        ('alarm interrupt only', 'RTC->CRH', 2),
        ('initial alarm', '(RTC->ALRH << 16) | RTC->ALRL', 2),
        ('CNF clear; synchronized; write finished', 'RTC->CRL & 0x38', 40),
        ('EXTI17 rising enabled', 'EXTI->IMR & EXTI->RTSR & (1 << 17)', 1 << 17),
        ('EXTI17 falling disabled', 'EXTI->FTSR & (1 << 17)', 0),
        ('global RTC IRQ disabled', 'NVIC->ISER[0] & (1 << 3)', 0),
        ('alarm IRQ enabled', 'NVIC->ISER[1] & (1 << 9)', 1 << 9),
        ('alarm vector', '(unsigned int)vectors[57] & ~1U', '(unsigned int)RTC_Alarm_IRQHandler & ~1U'),
        ('no RTC error', 'board_rtc_error', 0)
    ])


# Observe repeated RTC alarm delivery and publication of application events.
@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(target):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    target.reach("RTC_Alarm_IRQHandler")
    icsr = target.value("&SCB->ICSR")
    mask = target.value("SCB_ICSR_VECTACTIVE_Msk")
    before = target.value("board_rtc_events")
    previous_alarm = None

    # Observe repeated alarm delivery and confirm one event per interrupt.
    for index in range(2):
        # Check register and application state against the expected values.
        _check_values(target, [
            ('alarm exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 57),
            ('ALRF pending', 'RTC->CRL & RTC_CRL_ALRF', 2),
            ('EXTI17 pending', 'EXTI->PR & (1 << 17)', 1 << 17)
        ])

        target.check("one publication per IRQ", target.value("board_rtc_events"), (before + index) & 0xFFFFFFFF)

        alarm = target.value("(RTC->ALRH << 16) | RTC->ALRL")
        if previous_alarm is not None:
            # Verify alarm rearmed in thread.
            target.check("alarm rearmed in thread", ((alarm - previous_alarm) & 0xFFFFFFFF) >= 2, True)

        previous_alarm = alarm
        if index == 0:
            target.reach("RTC_Alarm_IRQHandler")

    target.reach("app_loop")

    # Verify thread resumes.
    target.check("thread resumes", target.value(f"*(unsigned int*){icsr} & {mask}"), 0)
    target.check("second event published", ((target.value("board_rtc_events") - before) & 0xFFFFFFFF) >= 2, True)
    target.check("no RTC error", target.value("board_rtc_error"), 0)


# Make the RTC wait predicate impossible and verify the bounded failure path.
@case("HW_CI_RTC_DEADLINE", labels=("rtc", "negative"), contracts=("ci_rtc_macros",))
def rtc_deadline(target):
    # TECH-002: docs/ru/TESTING_TECHNIQUES.md#tech-002 (EN: docs/en/TESTING_TECHNIQUES.md#tech-002).
    # TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
    target.reach("rtc_wait", when="error == 3")

    # Verify LSI wait mask.
    target.check("LSI wait mask", target.value("mask"), 1 << 1)

    before = target.value("board_ticks_ms")
    backup_address = target.value("&RCC->BDCR")
    backup = target.value(f"*(unsigned int*){backup_address}")

    # Make the ready predicate impossible without touching the oscillator/backup domain.
    target.set_value("mask", 0)
    target.reach("board_rtc_fault")

    # Check the timeout result without changing backup-domain state.
    target.check("RTC wait timeout reported", target.value("board_rtc_error"), 3)
    target.check("at least 1000 firmware ticks", ((target.value("board_ticks_ms") - before) & 0xFFFFFFFF) >= 1000, True)
    target.check("backup configuration unchanged", target.value(f"*(unsigned int*){backup_address}"), backup)
    target.check("no application loop", target.value("app_state.ticks"), 0)
    target.check("no alarm publication", target.value("board_rtc_events"), 0)

    target.report["injection_scope"] = "rtc_wait mask argument set to zero; not a physical LSI failure"
