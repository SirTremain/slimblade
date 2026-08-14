OUTPUT_ARCH(arm)
ENTRY(reset_trampoline)

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

ASSERT(ADDR(.text) == 0x22b4, "trampoline address changed")
ASSERT(SIZEOF(.text) == 8, "trampoline must remain two ARM instructions")
