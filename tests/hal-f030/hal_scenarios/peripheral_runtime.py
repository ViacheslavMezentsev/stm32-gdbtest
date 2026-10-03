"""
RU: Общие HAL-проверки периферии, измерений и управляемых отказов.
EN: Shared HAL peripheral runtime, measurement and controlled fault checks.
"""


# Observe HAL completion callbacks and validate published ADC samples.
def adc_dma_runtime(t, expected):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    for sequence in (1, 2):
        t.reach("HAL_ADC_ConvCpltCallback")

        # Check the ADC callback identity and completed DMA transfer.
        t.check("ADC callback handle", t.value("adc"), t.value("&" + expected["adc_handle"]))
        t.check("DMA exhausted", t.value(expected["dma_remaining"]), 0)

        t.reach("loop")

        # Check the publication counter before comparing measurement contents.
        t.check("published sequence", t.value("app_state.adc_sequences"), sequence)

        # Observe successive callbacks and check each published sample.
        for field in ("temperature_raw", "vrefint_raw"):
            raw = t.value("app_state." + field)
            t.report.setdefault("adc_raw", []).append({"field": field, "raw": raw})

            # Verify the current sample against its expected value and validity bounds.
            t.check(field + " non-saturated", 0 < raw < 4095, True)


# Observe timer interrupt handling and advancement of the event counter.
def timer_irq(t, expected):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    t.reach("HAL_TIM_PeriodElapsedCallback")

    # Check that the callback belongs to the configured timer.
    t.check("TIM callback handle", t.value("timer"), t.value("&" + expected["timer_handle"]))

    before = t.value("app_state.timer_events")
    t.reach("HAL_TIM_PeriodElapsedCallback")

    # Check event publication and the running timer state.
    t.check("TIM callback increment", t.value("app_state.timer_events"), before + 1)
    t.check("timer enabled", t.value(expected["timer_enabled"]), 1)


# Observe repeated RTC alarm delivery and publication of application events.
def rtc_alarm(t, expected):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    for count in (0, 1):
        t.reach("HAL_RTC_AlarmAEventCallback")

        # Check the alarm callback identity and event count.
        t.check("RTC callback handle", t.value("rtc"), t.value("&hrtc"))
        t.check("RTC repeated alarm", t.value("app_state.rtc_events"), count)

    t.reach("loop")

    # Check that the second alarm reached the application.
    t.check("RTC second event published", t.value("app_state.rtc_events"), 2)


# Force an ADC start error and verify that no sequence is published.
def adc_start_error(t, expected):
    # TECH-004: docs/ru/TESTING_TECHNIQUES.md#tech-004 (EN: docs/en/TESTING_TECHNIQUES.md#tech-004).
    t.reach("HAL_ADC_Start_DMA")
    t.force_return("(HAL_StatusTypeDef)1")
    t.reach("Error_Handler")

    # Check that the fault path did not publish a successful acquisition.
    t.check("no sequence published", t.value("app_state.adc_sequences"), 0)


# Suppress the completion callback and verify the application timeout path.
def adc_dma_timeout(t, expected):
    # TECH-004: docs/ru/TESTING_TECHNIQUES.md#tech-004 (EN: docs/en/TESTING_TECHNIQUES.md#tech-004).
    t.reach("HAL_ADC_ConvCpltCallback")

    # Suppress completion publication; DMA itself already completed.
    t.force_return("")
    t.reach("Error_Handler")

    # Check that suppressed completion cannot publish stale samples.
    t.check("no stale samples published", t.value("app_state.adc_sequences"), 0)


# Check measurement provenance and plausible VDDA and die temperature.
def adc_units(t, expected):
    t.reach("loop")
    t.reach("loop")
    quality = t.value("app_state.measurement.quality")
    supply = t.value("app_state.measurement.vdda_mv")
    temperature = t.value("app_state.measurement.temperature_mdeg_c")

    # Check measurement provenance and plausible physical ranges.
    t.check("conversion provenance", quality, expected["measurement_quality"])
    t.check("board supply plausible", 2800 <= supply <= 3600, True)

    # Broad board sanity only; no claim of calibrated temperature accuracy.
    t.check("die temperature plausible", -40000 <= temperature <= 125000, True)

    t.report["measurement"] = dict(vdda_mv=supply, temperature_mdeg_c=temperature, quality=quality)


# Reject invalid conversion inputs and verify subsequent measurement recovery.
def adc_invalid(t, expected):
    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for parameter, value in (("reference", 0), ("reference", 4095), ("temperature", 0)):
        t.reach("platform_adc_convert")
        t.set_value(parameter, str(value))
        t.reach("loop")

        # Check the published fields against the expected values.
        t.fields("app_state.measurement", {"quality": 0, "vdda_mv": 0, "temperature_mdeg_c": 0})

    t.reach("loop")

    # Check that valid acquisition resumes after the injected failures.
    t.check("measurement recovers", t.value("app_state.measurement.quality"), expected["measurement_quality"])


# Check conversion arithmetic against independent numerical reference vectors.
def adc_vectors(t, expected):
    # TECH-007: docs/ru/TESTING_TECHNIQUES.md#tech-007 (EN: docs/en/TESTING_TECHNIQUES.md#tech-007).
    # Analytic anchors supplied by the profile, independent of firmware arithmetic.
    for temp, ref, millivolts, degrees in expected["adc_vectors"]:
        t.reach("platform_adc_convert")
        temp = t.value(temp) if isinstance(temp, str) else temp
        ref = t.value(ref) if isinstance(ref, str) else ref
        t.set_value("temperature", str(temp))
        t.set_value("reference", str(ref))
        t.reach("loop")

        # Check the published fields against the expected values.
        t.fields("app_state.measurement", {"quality": expected["measurement_quality"],
                 "vdda_mv": millivolts, "temperature_mdeg_c": degrees})
