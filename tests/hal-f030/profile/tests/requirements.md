# Подготовленные требования NUCLEO-F030R8

Все сценарии ожидают аппаратной проверки. Остановки GDB влияют на тайминг;
число сценариев не является покрытием кода или измерением точности ADC.

## HW_BOOT
После reset достигаются main и loop. HardFault перехватывается отдельно.
## HW_CLOCK
HSI/SYSCLK/HCLK/PCLK 8 MHz, AHB/APB /1, clocks ADC1/TIM3/DMA1 включены.
## HW_GPIO
PA5 output push-pull, no pull, low speed, начальный Low (LD2 выключен).
## HW_BLINK
ODR5 принимает High/Low на следующих циклах измерения; uwTick >=500 ms между ними.
## HW_ADC_DMA_INIT
ADC1: 12 bit, forward scan только IN16/17, sampling 239.5 cycles, software start;
DMA1 Channel1 Normal с increment и halfword; конфигурация до запуска приложения.
## HW_TIM3_INIT
TIM3 PSC=7999, ARR=99, перед setup таймер ещё выключен; номинальный период 100 ms.
## HW_RTC_INIT
RTC от LSI, делители 127/311, output disabled. Точность LSI не проверяется.
## HW_ADC_DMA_RUNTIME
Два последовательных DMA завершения: hadc, CNDTR=0, счётчик и несатурированные данные.
## HW_TIM3_IRQ
Два callback htim3 увеличивают timer_events, TIM3 включён.
## HW_RTC_ALARM
Два Alarm A callback увеличивают rtc_events; повторное взведение работает.
## HW_ADC_START_ERROR
Принудительный HAL_ERROR из HAL_ADC_Start_DMA приводит в Error_Handler без публикации.
## HW_ADC_DMA_TIMEOUT
Подавлен callback завершения: приложение достигает Error_Handler без старых данных.
## HW_ADC_UNITS
quality=3, правдоподобные VDDA/температура; не подтверждает физическую точность.
## HW_ADC_INVALID
Нулевые/сатурированные входы дают ADC_INVALID, затем измерения восстанавливаются.
## HW_ADC_VECTORS
При TS_CAL1/VREFINT_CAL получаются 3300 mV и 30000 mC — опорная точка формулы.
## HW_SLEEP_SYSTICK
Sleep/WFI с активным SysTick, дедлайн >=500 ms, данные измерения сохраняются.
## HW_SLEEP_TIMER
При временном исключении SysTick IRQ приходит callback htim3, затем SysTick восстанавливается.
