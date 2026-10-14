ENTRY(reset_handler)
MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 32K
RAM (rw) : ORIGIN = 0x20000000, LENGTH = 64K }
PHDRS { code PT_LOAD FLAGS(5); ram PT_LOAD FLAGS(6); }
_stack_top = ORIGIN(RAM)+LENGTH(RAM);
SECTIONS {
 .vectors : { KEEP(*(.vectors)) } > FLASH :code
 .text : { *(.text*) *(.rodata*) } > FLASH :code
 .data : { *(.data*) } > RAM :ram
 .bss (NOLOAD) : { . = ALIGN(4); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > RAM :ram
}
