"""Sleep call path and IRQ progress, distinct from live DHCSR observation."""


def sleep_systick(t, expected):
    t.reach("app_idle")
    before = t.value("uwTick")
    t.reach("HAL_PWR_EnterSLEEPMode")
    t.check("WFI requested", t.value("SLEEPEntry"), t.value("PWR_SLEEPENTRY_WFI"))
    t.reach("SysTick_Handler")
    t.check("ordinary Sleep selected", t.value("SCB->SCR") & 4, 0)
    t.check("SysTick remains enabled", t.value("SysTick->CTRL") & 3, 3)
    t.reach("loop")
    t.check("idle deadline advanced", ((t.value("uwTick") - before) & 0xFFFFFFFF) >= 500, True)
    t.check("ADC sequence retained", t.value("app_state.adc_sequences"), 1)


def sleep_timer(t, expected):
    t.reach("HAL_PWR_EnterSLEEPMode")
    control = t.value("SysTick->CTRL") & 7
    # Temporarily exclude SysTick as a wake source. Teardown reset also restores it.
    t.set_value("SysTick->CTRL", str(control & ~2))
    before = t.value("app_state.timer_events")
    t.reach("HAL_TIM_PeriodElapsedCallback")
    t.check("timer callback", t.value("timer"), t.value("&" + expected["timer_handle"]))
    t.check("ordinary Sleep selected", t.value("SCB->SCR") & 4, 0)
    t.set_value("SysTick->CTRL", str(control))
    t.reach("loop")
    t.check("timer event processed", t.value("app_state.timer_events") > before, True)
    t.check("ADC sequence retained", t.value("app_state.adc_sequences"), 1)
