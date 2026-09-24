#include "stm32f4xx.h"
#include "cmsis_version.h"

void app_loop(void)
{
    GPIOC->ODR ^= GPIO_ODR_OD13;
    for (volatile unsigned delay = 0; delay < 800000; ++delay) {
        __NOP();
    }
}

int main(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;
    GPIOC->BSRR = GPIO_BSRR_BS13;
    GPIOC->MODER = (GPIOC->MODER & ~GPIO_MODER_MODER13) | GPIO_MODER_MODER13_0;
    for (;;) {
        app_loop();
    }
}
