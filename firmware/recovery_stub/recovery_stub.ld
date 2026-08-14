OUTPUT_ARCH(arm)
ENTRY(_vector_start)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00002020, LENGTH = 0x00025de0
    RAM   (rwx) : ORIGIN = 0x00400020, LENGTH = 0x00007fe0
}

SECTIONS
{
    .vectors :
    {
        KEEP(*(.vectors))
    } > FLASH

    .text :
    {
        *(.text .text.*)
        *(.rodata .rodata.*)
    } > FLASH

    .data :
    {
        *(.data .data.*)
    } > RAM AT> FLASH

    .bss (NOLOAD) :
    {
        *(.bss .bss.* COMMON)
    } > RAM

    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
        *(.comment)
    }
}

ASSERT(ADDR(.vectors) == 0x2020, "application vectors must start at 0x2020")
ASSERT(SIZEOF(.vectors) == 0x60, "vector/startup geometry changed")
ASSERT(ADDR(.text) == 0x2080, "Thumb code must start at 0x2080")
ASSERT(ADDR(.text) + SIZEOF(.text) <= 0x2800, "recovery stub grew unexpectedly")
ASSERT(SIZEOF(.data) == 0, "startup does not initialize .data")
ASSERT(SIZEOF(.bss) == 0, "startup does not initialize .bss")
