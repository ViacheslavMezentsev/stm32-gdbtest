"""E1 paired variants: only evidence writes change; MCU checks stay identical."""


def cmsis_adc_units(t):
    t.reach("board_adc_sample")
    t.reach("board_delay_ms")
    t.check("factory provenance", t.value("board_adc_reading.quality"), 2)
    t.check("plausible VDDA", 2800 <= t.value("board_adc_reading.vdda_mv") <= 3600, True)
    t.check("plausible die temperature", -40000 <= t.value("board_adc_reading.temperature_mdeg_c") <= 125000, True)
    t.record("measurement", {name: t.value("board_adc_reading." + name)
                            for name in ("vdda_mv", "temperature_mdeg_c", "quality")})


def hal_adc_units(t, expected):
    t.reach("loop")
    t.reach("loop")
    quality = t.value("app_state.measurement.quality")
    supply = t.value("app_state.measurement.vdda_mv")
    temperature = t.value("app_state.measurement.temperature_mdeg_c")
    t.check("conversion provenance", quality, expected["measurement_quality"])
    t.check("board supply plausible", 2800 <= supply <= 3600, True)
    t.check("die temperature plausible", -40000 <= temperature <= 125000, True)
    t.record("measurement", dict(vdda_mv=supply, temperature_mdeg_c=temperature, quality=quality))


def hal_blink(t, expected):
    t.reach("platform_adc_start")
    tick = t.value("uwTick")
    for level in (1 - expected["led_initial"], expected["led_initial"]):
        t.reach("platform_adc_start")
        t.check("LED pin toggled", t.value(expected["led_level"]), level)
        next_tick = t.value("uwTick")
        delta = (next_tick - tick) & 0xFFFFFFFF
        t.record("loop_tick_deltas_ms", delta)
        t.check("HAL delay >= 500 ms", delta >= 500, True)
        tick = next_tick
