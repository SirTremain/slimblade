ENTRY(candidate)
external_a = 0x9001;
external_b = 0x9101;
SECTIONS
{
    .text 0x1000 : { *(.text .text.*) }
    .ARM.exidx : { *(.ARM.exidx .ARM.exidx.*) }
    .rodata 0x2000 : { *(.rodata .rodata.*) }
    .data 0x3000 : { *(.data .data.*) }
    .bss 0x4000 (NOLOAD) : { *(.bss .bss.*) *(COMMON) }
    /DISCARD/ : { *(.comment) *(.note.GNU-stack) }
}
