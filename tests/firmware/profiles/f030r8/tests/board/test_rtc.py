"""
RU: Проверки настройки RTC, повторных прерываний и тайм-аута.
EN: RTC configuration, repeated alarm interrupts and deadline checks.
"""
from stm32_gdbtest import case

# LSI clocks the RTC (RM: 40 kHz nominal): 1 Hz = LSI / 128 / 312.
LSI_HZ = 40_000
RTC_PREDIV_A = 128 - 1
RTC_PREDIV_S = LSI_HZ // 128 - 1
# Two alarm events prove that the alarm is re-armed.
ALARM_EVENTS = 2
# EXTI line of the RTC alarm (RM, independent of the firmware).
RTC_ALARM_EXTI_LINE = 17
# board_rtc_error codes of the fixture firmware (rtc_*.c): 3 is the LSI-ready timeout.
RTC_ERROR_NONE = 0
RTC_ERROR_LSI_TIMEOUT = 3
# Firmware deadline of one RTC wait (rtc_*.c), in milliseconds.
RTC_WAIT_DEADLINE_MS = 1000

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF


# Verify RTC clock, calendar masks, alarm configuration and interrupt routing.
@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(t):
    t.reach("board_led_toggle")

    # Check register and application state against the expected values.
    t.check([
        ('LSI ready', 'RCC->CSR & RCC_CSR_LSIRDY'),
        ('LSI RTC clock enabled', 'RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)', 'RCC_BDCR_RTCEN | RCC_BDCR_RTCSEL_1'),
        ('RTC prescalers', 'RTC->PRER', RTC_PREDIV_A << 16 | RTC_PREDIV_S),
        ('24-hour Alarm A enabled with IRQ', 'RTC->CR', 'RTC_CR_ALRAE | RTC_CR_ALRAIE'),
        ('all calendar fields masked', 'RTC->ALRMAR',
         'RTC_ALRMAR_MSK4 | RTC_ALRMAR_MSK3 | RTC_ALRMAR_MSK2 | RTC_ALRMAR_MSK1'),
        ('subseconds masked', 'RTC->ALRMASSR', 0),
        ('initialization completed', 'RTC->ISR & RTC_ISR_INIT', 0),
        ('shadow synchronized', 'RTC->ISR & RTC_ISR_RSF'),
        ('EXTI17 enabled rising edge', f'(EXTI->IMR & EXTI->RTSR) & (1UL << {RTC_ALARM_EXTI_LINE})'),
        ('EXTI17 falling edge off', f'EXTI->FTSR & (1UL << {RTC_ALARM_EXTI_LINE})', 0),
        ('RTC NVIC enabled', 'NVIC->ISER[RTC_IRQn >> 5] & (1UL << (RTC_IRQn & 31))'),
        ('RTC vector', '(unsigned int)vectors[RTC_IRQn + 16] & ~1U', '(unsigned int)RTC_IRQHandler & ~1U'),
        ('no RTC error', 'board_rtc_error', RTC_ERROR_NONE)
    ])


# Observe repeated RTC alarm delivery and publication of application events.
@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(t):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    t.reach("RTC_IRQHandler")

    # TECH-002: preserve the CMSIS address/mask before entering HAL-free app.c.
    icsr_address = t.evaluate("&SCB->ICSR", as_type=int)
    active_mask = t.read("SCB_ICSR_VECTACTIVE_Msk")
    before = t.read("board_rtc_events")

    # Observe repeated alarm delivery and confirm one event per interrupt.
    for index in range(2):
        # Check register and application state against the expected values.
        t.check([
            ('RTC exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 'RTC_IRQn + 16'),
            ('Alarm A pending', 'RTC->ISR & RTC_ISR_ALRAF'),
            ('EXTI17 pending', f'EXTI->PR & (1UL << {RTC_ALARM_EXTI_LINE})')
        ])

        t.check("one event per handler", t.read("board_rtc_events"), (before + index) & U32_MASK)

        if index == 0:
            t.reach("RTC_IRQHandler")

    t.reach("app_loop")

    # Verify thread resumes.
    t.check("thread resumes", t.read(f"*(unsigned int*){icsr_address} & {active_mask}"), 0)
    t.check("second alarm published", ((t.read("board_rtc_events") - before) & U32_MASK) >= ALARM_EVENTS)
    t.check("no RTC error", t.read("board_rtc_error"), RTC_ERROR_NONE)


# Make the RTC wait predicate impossible and verify the bounded failure path.
@case("HW_CI_RTC_DEADLINE", timeout_s=90, labels=("rtc", "negative"), contracts=("ci_rtc_macros",))
def rtc_deadline(t):
    # TECH-002: docs/ru/TESTING_TECHNIQUES.md#tech-002 (EN: docs/en/TESTING_TECHNIQUES.md#tech-002).
    # TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
    # Stop at the call that reports the deadline error, then make the wait predicate impossible.
    t.reach("rtc_wait", condition=f"error == {RTC_ERROR_LSI_TIMEOUT}")
    t.check("rtc_wait received its error code", t.read("error"), RTC_ERROR_LSI_TIMEOUT)

    # Verify LSI wait mask.
    t.check("LSI wait mask", t.read("mask"), t.evaluate("RCC_CSR_LSIRDY"))

    before = t.read("board_ticks_ms")
    backup_address = t.evaluate("&RCC->BDCR", as_type=int)
    backup = t.read(f"*(unsigned int*){backup_address}")

    # Make the ready predicate impossible without touching the oscillator/backup domain.
    t.write("mask", 0)
    t.reach("board_rtc_fault")

    # Check the timeout result without changing backup-domain state.
    t.check("RTC wait timeout reported", t.read("board_rtc_error"), RTC_ERROR_LSI_TIMEOUT)
    t.check("at least 1000 firmware ticks", ((t.read("board_ticks_ms") - before) & U32_MASK) >= RTC_WAIT_DEADLINE_MS)
    t.check("backup configuration unchanged", t.read(f"*(unsigned int*){backup_address}"), backup)
    t.check("no application loop", t.read("app_state.ticks"), 0)
    t.check("no alarm publication", t.read("board_rtc_events"), 0)

    t.report["injection_scope"] = "rtc_wait mask argument set to zero; not a physical LSI failure"
