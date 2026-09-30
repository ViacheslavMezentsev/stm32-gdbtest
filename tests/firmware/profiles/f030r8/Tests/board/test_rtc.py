from stm32_gdbtest import case


@case("HW_CI_RTC_INIT", labels=("rtc", "init"), contracts=("ci_rtc_macros",))
def rtc_init(target):
    target.reach("board_led_toggle")
    target.check("LSI ready", target.value("(RCC->CSR & RCC_CSR_LSIRDY) != 0"), 1)
    target.check("LSI RTC clock enabled", target.value("RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)"), 0x8200)
    target.check("RTC prescalers", target.value("RTC->PRER"), (127 << 16) | 311)
    target.check("24-hour Alarm A enabled with IRQ", target.value("RTC->CR"), 0x1100)
    target.check("all calendar fields masked", target.value("RTC->ALRMAR"), 0x80808080)
    target.check("subseconds masked", target.value("RTC->ALRMASSR"), 0)
    target.check("initialization completed", target.value("RTC->ISR & RTC_ISR_INIT"), 0)
    target.check("shadow synchronized", target.value("(RTC->ISR & RTC_ISR_RSF) != 0"), 1)
    target.check("EXTI17 enabled rising edge", target.value("(EXTI->IMR & EXTI->RTSR) & (1 << 17)"), 1 << 17)
    target.check("EXTI17 falling edge off", target.value("EXTI->FTSR & (1 << 17)"), 0)
    target.check("RTC NVIC enabled", target.value("NVIC->ISER[0] & (1 << 2)"), 1 << 2)
    target.check("RTC vector", target.value("(unsigned int)vectors[18] & ~1U"), target.value("(unsigned int)RTC_IRQHandler & ~1U"))
    target.check("no RTC error", target.value("board_rtc_error"), 0)


@case("HW_CI_RTC_ALARM", labels=("rtc", "irq"), contracts=("ci_rtc_macros",))
def rtc_alarm(target):
    target.reach("RTC_IRQHandler")
    before = target.value("board_rtc_events")
    for index in range(2):
        target.check("RTC exception", target.value("$xPSR & 0x1ff"), 18)
        target.check("Alarm A pending", target.value("(RTC->ISR & RTC_ISR_ALRAF) != 0"), 1)
        target.check("EXTI17 pending", target.value("EXTI->PR & (1 << 17)"), 1 << 17)
        target.check("one event per handler", target.value("board_rtc_events"), (before + index) & 0xFFFFFFFF)
        if index == 0:
            target.reach("RTC_IRQHandler")
    target.reach("app_loop")
    target.check("thread resumes", target.value("$xPSR & 0x1ff"), 0)
    target.check("second alarm published", ((target.value("board_rtc_events") - before) & 0xFFFFFFFF) >= 2, True)
    target.check("no RTC error", target.value("board_rtc_error"), 0)
