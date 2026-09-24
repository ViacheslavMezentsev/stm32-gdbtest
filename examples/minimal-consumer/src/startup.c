#include <stdint.h>

extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern int main(void);
void HardFault_Handler(void) { for (;;) {} }
void MemManage_Handler(void) { for (;;) {} }
void BusFault_Handler(void) { for (;;) {} }
void UsageFault_Handler(void) { for (;;) {} }
void Default_Handler(void) { for (;;) {} }
void Reset_Handler(void)
{
    uint32_t *source = &_sidata;
    for (uint32_t *dest = &_sdata; dest < &_edata;) { *dest++ = *source++; }
    for (uint32_t *dest = &_sbss; dest < &_ebss;) { *dest++ = 0; }
    (void)main();
    for (;;) {}
}
__attribute__((section(".isr_vector"), used))
void (*const vectors[])(void) = {
    (void (*)(void))(&_estack), Reset_Handler, Default_Handler,
    HardFault_Handler, MemManage_Handler, BusFault_Handler, UsageFault_Handler,
    0, 0, 0, 0, Default_Handler, Default_Handler, 0, Default_Handler, Default_Handler
};
