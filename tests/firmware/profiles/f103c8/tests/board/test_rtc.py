from stm32_gdbtest import case


@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(target):
    target.reach("board_led_toggle")
    target.check("LSI ready", target.value("(RCC->CSR & RCC_CSR_LSIRDY) != 0"), 1)
    target.check("LSI RTC clock", target.value("RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)"), 0x8200)
    target.check("F1 prescaler", target.value("(RTC->PRLH << 16) | RTC->PRLL"), 39999)
    target.check("alarm interrupt only", target.value("RTC->CRH"), 2)
    target.check("initial alarm", target.value("(RTC->ALRH << 16) | RTC->ALRL"), 2)
    target.check("CNF clear; synchronized; write finished", target.value("RTC->CRL & 0x38"), 0x28)
    target.check("EXTI17 rising enabled", target.value("EXTI->IMR & EXTI->RTSR & (1 << 17)"), 1 << 17)
    target.check("EXTI17 falling disabled", target.value("EXTI->FTSR & (1 << 17)"), 0)
    target.check("global RTC IRQ disabled", target.value("NVIC->ISER[0] & (1 << 3)"), 0)
    target.check("alarm IRQ enabled", target.value("NVIC->ISER[1] & (1 << 9)"), 1 << 9)
    target.check("alarm vector", target.value("(unsigned int)vectors[57] & ~1U"), target.value("(unsigned int)RTC_Alarm_IRQHandler & ~1U"))
    target.check("no RTC error", target.value("board_rtc_error"), 0)


@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(target):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    target.reach("RTC_Alarm_IRQHandler")
    icsr = target.value("&SCB->ICSR")
    mask = target.value("SCB_ICSR_VECTACTIVE_Msk")
    before = target.value("board_rtc_events")
    previous_alarm = None
    for index in range(2):
        target.check("alarm exception", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 57)
        target.check("ALRF pending", target.value("RTC->CRL & RTC_CRL_ALRF"), 2)
        target.check("EXTI17 pending", target.value("EXTI->PR & (1 << 17)"), 1 << 17)
        target.check("one publication per IRQ", target.value("board_rtc_events"), (before + index) & 0xFFFFFFFF)
        alarm = target.value("(RTC->ALRH << 16) | RTC->ALRL")
        if previous_alarm is not None:
            target.check("alarm rearmed in thread", ((alarm - previous_alarm) & 0xFFFFFFFF) >= 2, True)
        previous_alarm = alarm
        if index == 0:
            target.reach("RTC_Alarm_IRQHandler")
    target.reach("app_loop")
    target.check("thread resumes", target.value(f"*(unsigned int*){icsr} & {mask}"), 0)
    target.check("second event published", ((target.value("board_rtc_events") - before) & 0xFFFFFFFF) >= 2, True)
    target.check("no RTC error", target.value("board_rtc_error"), 0)


@case("HW_CI_RTC_DEADLINE", labels=("rtc", "negative"), contracts=("ci_rtc_macros",))
def rtc_deadline(target):
    # TECH-002: docs/ru/TESTING_TECHNIQUES.md#tech-002 (EN: docs/en/TESTING_TECHNIQUES.md#tech-002).
    # TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
    target.reach("rtc_wait", when="error == 3")
    target.check("LSI wait mask", target.value("mask"), 1 << 1)
    before = target.value("board_ticks_ms")
    backup_address = target.value("&RCC->BDCR")
    backup = target.value(f"*(unsigned int*){backup_address}")
    # Make the ready predicate impossible without touching the oscillator/backup domain.
    target.set_value("mask", 0)
    target.reach("board_rtc_fault")
    target.check("RTC wait timeout reported", target.value("board_rtc_error"), 3)
    target.check("at least 1000 firmware ticks", ((target.value("board_ticks_ms") - before) & 0xFFFFFFFF) >= 1000, True)
    target.check("backup configuration unchanged", target.value(f"*(unsigned int*){backup_address}"), backup)
    target.check("no application loop", target.value("app_state.ticks"), 0)
    target.check("no alarm publication", target.value("board_rtc_events"), 0)
    target.report["injection_scope"] = "rtc_wait mask argument set to zero; not a physical LSI failure"
