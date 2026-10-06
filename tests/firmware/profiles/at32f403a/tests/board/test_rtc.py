"""
RU: Проверки RTC AT32F403A: настройка, повторные прерывания будильника и тайм-аут.
EN: AT32F403A RTC configuration, repeated alarm interrupts and deadline checks.
"""
from stm32_gdbtest import case


# LICK clocks the RTC (RM: 40 kHz nominal, not a precision reference).
LICK_HZ = 40_000
# The firmware arms the first alarm at 2 s and re-arms it every 2 s.
FIRST_ALARM_S = 2
ALARM_PERIOD_S = 2
# EXINT line of the RTC alarm (RM, independent of the firmware) and the RTC clock selection code of LICK.
RTC_ALARM_EXINT_LINE = 17
RTCSEL_LICK = 2
# board_rtc_error codes of the fixture firmware (rtc_*.c): 3 is the LICK-stable timeout.
RTC_ERROR_NONE = 0
RTC_ERROR_LICK_TIMEOUT = 3
# Firmware deadline of one RTC wait (rtc_*.c), in milliseconds.
RTC_WAIT_DEADLINE_MS = 1000
# LICKSTBL bit of CRM_CTRLSTS and TAIEN bit of RTC_CTRLH (RM): the wait mask and the only enabled RTC interrupt.
CRM_CTRLSTS_LICKSTBL = 1 << 1
RTC_CTRLH_TAIEN = 1 << 1

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF


# Verify RTC clock, divider, alarm configuration and interrupt routing.
@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(t):
    t.reach("board_led_toggle")

    # Check register and application state against the expected values.
    t.check([
        ('LICK stable', 'CRM->ctrlsts_bit.lickstbl', 1),
        ('LICK RTC clock', 'CRM->bpdc_bit.rtcsel', RTCSEL_LICK),
        ('RTC clock enabled', 'CRM->bpdc_bit.rtcen', 1),
        ('divider', '(RTC->divh << 16) | RTC->divl', LICK_HZ - 1),
        ('alarm interrupt only', 'RTC->ctrlh', RTC_CTRLH_TAIEN),
        ('initial alarm', '(RTC->tah << 16) | RTC->tal', FIRST_ALARM_S),
        ('synchronized', 'RTC->ctrll_bit.updf', 1),
        ('configuration mode off', 'RTC->ctrll_bit.cfgen', 0),
        ('write finished', 'RTC->ctrll_bit.cfgf', 1),
        ('EXINT17 rising enabled', f'EXINT->inten & EXINT->polcfg1 & (1UL << {RTC_ALARM_EXINT_LINE})'),
        ('EXINT17 falling disabled', f'EXINT->polcfg2 & (1UL << {RTC_ALARM_EXINT_LINE})', 0),
        ('global RTC IRQ disabled', 'NVIC->ISER[RTC_IRQn >> 5] & (1UL << (RTC_IRQn & 31))', 0),
        ('alarm IRQ enabled', 'NVIC->ISER[RTCAlarm_IRQn >> 5] & (1UL << (RTCAlarm_IRQn & 31))'),
        ('alarm vector', '(unsigned int)vectors[RTCAlarm_IRQn + 16] & ~1U',
         '(unsigned int)RTC_Alarm_IRQHandler & ~1U'),
        ('no RTC error', 'board_rtc_error', RTC_ERROR_NONE)
    ])


# Observe repeated RTC alarm delivery and publication of application events.
@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(t):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    t.reach("RTC_Alarm_IRQHandler")
    icsr = t.evaluate("&SCB->ICSR", as_type=int)
    mask = t.read("SCB_ICSR_VECTACTIVE_Msk")
    before = t.read("board_rtc_events")
    previous_alarm = None

    # Observe repeated alarm delivery and confirm one event per interrupt.
    for index in range(2):
        # Check register and application state against the expected values.
        t.check([
            ('alarm exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 'RTCAlarm_IRQn + 16'),
            ('alarm flag pending', 'RTC->ctrll_bit.taf', 1),
            ('EXINT17 pending', f'EXINT->intsts & (1UL << {RTC_ALARM_EXINT_LINE})')
        ])

        t.check("one publication per IRQ", t.read("board_rtc_events"), (before + index) & U32_MASK)

        alarm = t.read("(RTC->tah << 16) | RTC->tal")
        if previous_alarm is not None:
            # Verify alarm rearmed in thread.
            t.check("alarm rearmed in thread", ((alarm - previous_alarm) & U32_MASK) >= ALARM_PERIOD_S)

        previous_alarm = alarm
        if index == 0:
            t.reach("RTC_Alarm_IRQHandler")

    t.reach("app_loop")

    # Verify thread resumes.
    t.check("thread resumes", t.read(f"*(unsigned int*){icsr} & {mask}"), 0)
    t.check("second event published", ((t.read("board_rtc_events") - before) & U32_MASK) >= ALARM_PERIOD_S)
    t.check("no RTC error", t.read("board_rtc_error"), RTC_ERROR_NONE)


# Make the RTC wait predicate impossible and verify the bounded failure path.
@case("HW_CI_RTC_DEADLINE", timeout_s=90, labels=("rtc", "negative"), contracts=("ci_rtc_macros",))
def rtc_deadline(t):
    # TECH-002: docs/ru/TESTING_TECHNIQUES.md#tech-002 (EN: docs/en/TESTING_TECHNIQUES.md#tech-002).
    # TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
    # Stop at the call that reports the deadline error, then make the wait predicate impossible.
    t.reach("rtc_wait", condition=f"error == {RTC_ERROR_LICK_TIMEOUT}")
    t.check("rtc_wait received its error code", t.read("error"), RTC_ERROR_LICK_TIMEOUT)

    # Verify LICK wait mask.
    t.check("LICK wait mask", t.read("mask"), CRM_CTRLSTS_LICKSTBL)

    before = t.read("board_ticks_ms")
    backup_address = t.evaluate("&CRM->bpdc", as_type=int)
    backup = t.read(f"*(unsigned int*){backup_address}")

    # Make the ready predicate impossible without touching the oscillator/battery domain.
    t.write("mask", 0)
    t.reach("board_rtc_fault")

    # Check the timeout result without changing battery-domain state.
    t.check("RTC wait timeout reported", t.read("board_rtc_error"), RTC_ERROR_LICK_TIMEOUT)
    t.check("at least 1000 firmware ticks", ((t.read("board_ticks_ms") - before) & U32_MASK) >= RTC_WAIT_DEADLINE_MS)
    t.check("battery domain configuration unchanged", t.read(f"*(unsigned int*){backup_address}"), backup)
    t.check("no application loop", t.read("app_state.ticks"), 0)
    t.check("no alarm publication", t.read("board_rtc_events"), 0)

    t.report["injection_scope"] = "rtc_wait mask argument set to zero; not a physical LICK failure"
