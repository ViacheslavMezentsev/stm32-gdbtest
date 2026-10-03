from stm32_gdbtest import case




def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)
        target.check(name, actual, expected)


@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(target):
    target.reach("board_led_toggle")
    _check_values(target, [
        ('LSI ready', '(RCC->CSR & RCC_CSR_LSIRDY) != 0', 1),
        ('LSI RTC clock enabled', 'RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)', 33280),
        ('RTC prescalers', 'RTC->PRER', 127 << 16 | 249),
        ('24-hour Alarm A enabled with IRQ', 'RTC->CR', 4352),
        ('all calendar fields masked', 'RTC->ALRMAR', 2155905152),
        ('subseconds masked', 'RTC->ALRMASSR', 0),
        ('initialization completed', 'RTC->ISR & RTC_ISR_INIT', 0),
        ('shadow synchronized', '(RTC->ISR & RTC_ISR_RSF) != 0', 1),
        ('EXTI17 enabled rising edge', '(EXTI->IMR & EXTI->RTSR) & (1 << 17)', 1 << 17),
        ('EXTI17 falling edge off', 'EXTI->FTSR & (1 << 17)', 0),
        ('RTC NVIC enabled', 'NVIC->ISER[1] & (1 << 9)', 1 << 9),
        ('RTC vector', '(unsigned int)vectors[57] & ~1U', '(unsigned int)RTC_Alarm_IRQHandler & ~1U'),
        ('no RTC error', 'board_rtc_error', 0),
    ])


@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(target):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    target.reach("RTC_Alarm_IRQHandler")
    # TECH-002: preserve the CMSIS address/mask before entering HAL-free app.c.
    icsr_address = target.value("&SCB->ICSR")
    active_mask = target.value("SCB_ICSR_VECTACTIVE_Msk")
    before = target.value("board_rtc_events")
    for index in range(2):
        _check_values(target, [
            ('RTC exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 57),
            ('Alarm A pending', '(RTC->ISR & RTC_ISR_ALRAF) != 0', 1),
            ('EXTI17 pending', 'EXTI->PR & (1 << 17)', 1 << 17),
        ])
        target.check("one event per handler", target.value("board_rtc_events"), (before + index) & 0xFFFFFFFF)
        if index == 0:
            target.reach("RTC_Alarm_IRQHandler")
    target.reach("app_loop")
    target.check("thread resumes", target.value(f"*(unsigned int*){icsr_address} & {active_mask}"), 0)
    target.check("second alarm published", ((target.value("board_rtc_events") - before) & 0xFFFFFFFF) >= 2, True)
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
