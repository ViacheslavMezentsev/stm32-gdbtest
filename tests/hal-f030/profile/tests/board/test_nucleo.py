"""Validated on Nucleo F030R8 via onboard J-Link STLink/SWD."""
from stm32_gdbtest import case
from hal_scenarios import board, power
from hal_scenarios import peripheral_runtime as runtime
from hal_scenarios.expectations import EXPECTED


@case('HW_BOOT', timeout_s=30, labels=('boot',), contracts=('application',))
def boot(t):
    board.boot(t, EXPECTED)


@case('HW_CLOCK', timeout_s=30, labels=('rcc',), contracts=('clock_macros',))
def clock(t):
    board.clock(t, EXPECTED)


@case('HW_GPIO', timeout_s=30, labels=('gpio',), contracts=('gpio_macros',))
def gpio(t):
    board.gpio(t, EXPECTED)


@case('HW_BLINK', timeout_s=30, labels=('gpio', 'tick'), contracts=('gpio_macros',))
def blink(t):
    board.blink(t, EXPECTED)


@case('HW_ADC_DMA_RUNTIME', timeout_s=30, labels=('adc', 'dma', 'runtime'), contracts=('runtime_macros',))
def adc_dma_runtime(t):
    runtime.adc_dma_runtime(t, EXPECTED)


@case('HW_TIM3_IRQ', timeout_s=30, labels=('tim', 'irq', 'runtime'), contracts=('runtime_macros',))
def timer_irq(t):
    runtime.timer_irq(t, EXPECTED)


@case('HW_RTC_ALARM', timeout_s=30, labels=('rtc', 'irq', 'runtime'), contracts=())
def rtc_alarm(t):
    runtime.rtc_alarm(t, EXPECTED)


@case('HW_ADC_START_ERROR', timeout_s=30, labels=('adc', 'injection'), contracts=('adc_start_error',))
def adc_start_error(t):
    runtime.adc_start_error(t, EXPECTED)


@case('HW_ADC_DMA_TIMEOUT', timeout_s=30, labels=('adc', 'dma', 'injection'), contracts=('adc_dma_timeout',))
def adc_dma_timeout(t):
    runtime.adc_dma_timeout(t, EXPECTED)


@case('HW_ADC_UNITS', timeout_s=30, labels=('adc', 'units'), contracts=())
def adc_units(t):
    runtime.adc_units(t, EXPECTED)


@case('HW_ADC_INVALID', timeout_s=30, labels=('adc', 'units'), contracts=())
def adc_invalid(t):
    runtime.adc_invalid(t, EXPECTED)


@case('HW_ADC_VECTORS', timeout_s=30, labels=('adc', 'units'), contracts=())
def adc_vectors(t):
    runtime.adc_vectors(t, EXPECTED)


@case('HW_SLEEP_SYSTICK', timeout_s=30, labels=('pwr', 'sleep'), contracts=())
def sleep_systick(t):
    power.sleep_systick(t, EXPECTED)


@case('HW_SLEEP_TIMER', timeout_s=30, labels=('pwr', 'sleep', 'injection'), contracts=('runtime_macros',))
def sleep_timer(t):
    power.sleep_timer(t, EXPECTED)
