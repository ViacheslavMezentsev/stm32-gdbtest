"""
RU: Проверки пути Sleep и продвижения после прерывания.
EN: Sleep call-path checks and progress after interrupts.
"""

# Idle period of the HAL fixture (app_idle), in milliseconds.
IDLE_MS = 500
# HAL tick counter uwTick is a uint32_t and wraps around.
U32_MASK = 0xFFFFFFFF


# Verify ordinary Sleep and application progress after a SysTick interrupt.
def sleep_systick(t, expected):
    t.reach("app_idle")
    before = t.read("uwTick")
    t.reach("HAL_PWR_EnterSLEEPMode")

    # Check the requested Sleep entry and the active wake source.
    t.check("WFI requested", t.read("SLEEPEntry"), t.evaluate("PWR_SLEEPENTRY_WFI"))

    t.reach("SysTick_Handler")

    # Verify ordinary Sleep selected.
    t.check("ordinary Sleep selected", t.read("SCB->SCR & SCB_SCR_SLEEPDEEP_Msk"), 0)
    t.check("SysTick remains enabled", t.read("SysTick->CTRL & (SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk)"),
            t.evaluate("SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk"))

    t.reach("loop")

    # Check elapsed idle time and retained ADC publication.
    t.check("idle deadline advanced", ((t.read("uwTick") - before) & U32_MASK) >= IDLE_MS)
    t.check("ADC sequence retained", t.read("app_state.adc_sequences"), 1)


# Exclude SysTick temporarily and verify timer-driven progress through Sleep.
def sleep_timer(t, expected):
    t.reach("HAL_PWR_EnterSLEEPMode")

    # Only the bits the application sets are saved: counter, interrupt and core clock source.
    running = "SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk"
    control = t.read(f"SysTick->CTRL & ({running})")

    # Temporarily exclude SysTick as a wake source. Teardown reset also restores it.
    t.write("SysTick->CTRL", control & ~t.evaluate("SysTick_CTRL_TICKINT_Msk"))
    before = t.read("app_state.timer_events")
    t.reach("HAL_TIM_PeriodElapsedCallback")

    # Verify timer callback.
    t.check("timer callback", t.read("timer"), t.read("&" + expected["timer_handle"]))
    t.check("ordinary Sleep selected", t.read("SCB->SCR & SCB_SCR_SLEEPDEEP_Msk"), 0)

    t.write("SysTick->CTRL", control)
    t.reach("loop")

    # Verify timer event processed.
    t.check("timer event processed", t.read("app_state.timer_events") > before)
    t.check("ADC sequence retained", t.read("app_state.adc_sequences"), 1)
