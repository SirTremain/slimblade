OUTPUT_ARCH(arm)
ENTRY(startup_trampoline)

MEMORY
{
    TRAMPOLINE (rx) : ORIGIN = 0x000022b4, LENGTH = 0x0000004c
}

SECTIONS
{
    .text :
    {
        *(.text .text.*)
    } > TRAMPOLINE

    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
        *(.comment)
    }
}

ASSERT(ADDR(.text) == 0x22b4, "startup trampoline address changed")
ASSERT(ADDR(.text) + SIZEOF(.text) <= 0x2300, "startup trampoline overlaps IRQ")
