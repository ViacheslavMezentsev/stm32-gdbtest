ENTRY(Reset_Handler)
MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 64K
         RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 64K }
SECTIONS { .text : { KEEP(*(.vectors)) *(.text*) *(.rodata*) } > FLASH
           .experiment (NOLOAD) : { KEEP(*(.experiment)) } > RAM
           .data : { *(.data*) } > RAM
           .bss : { *(.bss*) *(COMMON) } > RAM }
