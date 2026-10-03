"""
RU: Проверки пути Sleep и продвижения после прерывания.
EN: Sleep call-path checks and progress after interrupts.
"""


# Verify ordinary Sleep and application progress after a SysTick interrupt.
def sleep_systick(t, expected):
    t.reach("app_idle")
    before = t.value("uwTick")
    t.reach("HAL_PWR_EnterSLEEPMode")

    # Check the requested Sleep entry and the active wake source.
    t.check("WFI requested", t.value("SLEEPEntry"), t.value("PWR_SLEEPENTRY_WFI"))

    t.reach("SysTick_Handler")

    # Verify ordinary Sleep selected.
    t.check("ordinary Sleep selected", t.value("SCB->SCR") & 4, 0)
    t.check("SysTick remains enabled", t.value("SysTick->CTRL") & 3, 3)

    t.reach("loop")

    # Check elapsed idle time and retained ADC publication.
    t.check("idle deadline advanced", ((t.value("uwTick") - before) & 0xFFFFFFFF) >= 500, True)
    t.check("ADC sequence retained", t.value("app_state.adc_sequences"), 1)


# Exclude SysTick temporarily and verify timer-driven progress through Sleep.
def sleep_timer(t, expected):
    t.reach("HAL_PWR_EnterSLEEPMode")
    control = t.value("SysTick->CTRL") & 7

    # Temporarily exclude SysTick as a wake source. Teardown reset also restores it.
    t.set_value("SysTick->CTRL", str(control & ~2))
    before = t.value("app_state.timer_events")
    t.reach("HAL_TIM_PeriodElapsedCallback")

    # Verify timer callback.
    t.check("timer callback", t.value("timer"), t.value("&" + expected["timer_handle"]))
    t.check("ordinary Sleep selected", t.value("SCB->SCR") & 4, 0)

    t.set_value("SysTick->CTRL", str(control))
    t.reach("loop")

    # Verify timer event processed.
    t.check("timer event processed", t.value("app_state.timer_events") > before, True)
    t.check("ADC sequence retained", t.value("app_state.adc_sequences"), 1)
