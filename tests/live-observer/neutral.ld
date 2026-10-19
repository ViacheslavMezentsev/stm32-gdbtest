ENTRY(Reset_Handler)
MEMORY { FLASH(rx): ORIGIN = 0x08000000, LENGTH = 64K
 RAM(rwx): ORIGIN = 0x20000000, LENGTH = 28K
 OBS(rwx): ORIGIN = 0x20008000, LENGTH = 4K }
SECTIONS {
 .text : { KEEP(*(.vectors)) *(.text*) *(.rodata*) } > FLASH
 .data : { *(.data*) } > RAM
 .bss (NOLOAD) : { *(.bss*) *(COMMON) } > RAM
 .observer (NOLOAD) : { __observer_start = .; . += 4096; __observer_end = .; } > OBS
}
