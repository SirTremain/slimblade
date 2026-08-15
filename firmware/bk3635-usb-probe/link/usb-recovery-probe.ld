OUTPUT_ARCH(arm)
ENTRY(_vector_start)

MEMORY
{
    FLASH (rx) : ORIGIN = 0x00002020, LENGTH = 0x00025de0
}

SECTIONS
{
    .vectors 0x00002020 :
    {
        KEEP(*(.vectors))
    } > FLASH

    .guard_prefix 0x00002080 :
    {
        KEEP(*(.text.guard_prefix))
        KEEP(*(.text.stock_delay))
    } > FLASH

    .experiment 0x000021c4 :
    {
        KEEP(*(.text.rust_experiment))
        *(.text)
        *(.text.*)
        *(.rodata)
        *(.rodata.*)
    } > FLASH

    .data :
    {
        *(.data)
        *(.data.*)
    } > FLASH

    .bss (NOLOAD) :
    {
        *(.bss)
        *(.bss.*)
        *(COMMON)
    } > FLASH

    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
        *(.comment)
    }
}

ASSERT(ADDR(.vectors) == 0x2020, "vectors must start at 0x2020")
ASSERT(SIZEOF(.vectors) == 0x60, "vector and ARM reset bytes must total 0x60")
ASSERT(ADDR(.guard_prefix) == 0x2080, "guard prefix must start at 0x2080")
ASSERT(SIZEOF(.guard_prefix) == 0x144, "live-tested guard prefix must total 0x144")
ASSERT(ADDR(.experiment) == 0x21c4, "USB experiment must start at 0x21c4")
ASSERT(SIZEOF(.data) == 0, "USB probe must not require initialized RAM")
ASSERT(SIZEOF(.bss) == 0, "USB probe must not require zeroed RAM")
