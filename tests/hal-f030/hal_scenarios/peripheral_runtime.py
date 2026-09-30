"""F030 HAL scenario helpers; source and migration hashes: provenance/source.json."""

def adc_dma_runtime(t, expected):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    for sequence in (1, 2):
        t.reach("HAL_ADC_ConvCpltCallback")
        t.check("ADC callback handle", t.value("adc"), t.value("&" + expected["adc_handle"]))
        t.check("DMA exhausted", t.value(expected["dma_remaining"]), 0)
        t.reach("loop")
        t.check("published sequence", t.value("app_state.adc_sequences"), sequence)
        for field in ("temperature_raw", "vrefint_raw"):
            raw = t.value("app_state." + field)
            t.report.setdefault("adc_raw", []).append({"field": field, "raw": raw})
            t.check(field + " non-saturated", 0 < raw < 4095, True)

def timer_irq(t, expected):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    t.reach("HAL_TIM_PeriodElapsedCallback")
    t.check("TIM callback handle", t.value("timer"), t.value("&" + expected["timer_handle"]))
    before = t.value("app_state.timer_events")
    t.reach("HAL_TIM_PeriodElapsedCallback")
    t.check("TIM callback increment", t.value("app_state.timer_events"), before + 1)
    t.check("timer enabled", t.value(expected["timer_enabled"]), 1)

def rtc_alarm(t, expected):
    # TECH-003: docs/ru/TESTING_TECHNIQUES.md#tech-003 (EN: docs/en/TESTING_TECHNIQUES.md#tech-003).
    for count in (0, 1):
        t.reach("HAL_RTC_AlarmAEventCallback")
        t.check("RTC callback handle", t.value("rtc"), t.value("&hrtc"))
        t.check("RTC repeated alarm", t.value("app_state.rtc_events"), count)
    t.reach("loop")
    t.check("RTC second event published", t.value("app_state.rtc_events"), 2)

def adc_start_error(t, expected):
    # TECH-004: docs/ru/TESTING_TECHNIQUES.md#tech-004 (EN: docs/en/TESTING_TECHNIQUES.md#tech-004).
    t.reach("HAL_ADC_Start_DMA")
    t.force_return("(HAL_StatusTypeDef)1")
    t.reach("Error_Handler")
    t.check("no sequence published", t.value("app_state.adc_sequences"), 0)

def adc_dma_timeout(t, expected):
    # TECH-004: docs/ru/TESTING_TECHNIQUES.md#tech-004 (EN: docs/en/TESTING_TECHNIQUES.md#tech-004).
    t.reach("HAL_ADC_ConvCpltCallback")
    # Suppress completion publication; DMA itself already completed.
    t.force_return("")
    t.reach("Error_Handler")
    t.check("no stale samples published", t.value("app_state.adc_sequences"), 0)


def adc_units(t, expected):
    t.reach("loop")
    t.reach("loop")
    quality = t.value("app_state.measurement.quality")
    supply = t.value("app_state.measurement.vdda_mv")
    temperature = t.value("app_state.measurement.temperature_mdeg_c")
    t.check("conversion provenance", quality, expected["measurement_quality"])
    t.check("board supply plausible", 2800 <= supply <= 3600, True)
    # Broad board sanity only; no claim of calibrated temperature accuracy.
    t.check("die temperature plausible", -40000 <= temperature <= 125000, True)
    t.report["measurement"] = dict(vdda_mv=supply, temperature_mdeg_c=temperature, quality=quality)


def adc_invalid(t, expected):
    for parameter, value in (("reference", 0), ("reference", 4095), ("temperature", 0)):
        t.reach("platform_adc_convert")
        t.set_value(parameter, str(value))
        t.reach("loop")
        t.fields("app_state.measurement", {"quality": 0, "vdda_mv": 0, "temperature_mdeg_c": 0})
    t.reach("loop")
    t.check("measurement recovers", t.value("app_state.measurement.quality"), expected["measurement_quality"])


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
        t.fields("app_state.measurement", {"quality": expected["measurement_quality"],
                 "vdda_mv": millivolts, "temperature_mdeg_c": degrees})
