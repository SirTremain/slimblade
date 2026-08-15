OUTPUT_ARCH(arm)
ENTRY(startup_trampoline)

MEMORY
{
    CARRIER (rx) : ORIGIN = 0x000021ac, LENGTH = 0x00000120
    TRAMPOLINE (rx) : ORIGIN = 0x000022cc, LENGTH = 0x00000034
}

SECTIONS
{
    .carrier 0x000021ac :
    {
        KEEP(*(.text.carrier))
    } > CARRIER

    .trampoline 0x000022cc :
    {
        KEEP(*(.text.trampoline))
    } > TRAMPOLINE

    /DISCARD/ :
    {
        *(.text)
        *(.text.*)
        *(.rodata*)
        *(.data*)
        *(.bss*)
        *(.ARM.exidx*)
        *(.ARM.extab*)
        *(.comment)
    }
}

ASSERT(ADDR(.carrier) == 0x21ac, "carrier address changed")
ASSERT(ADDR(.carrier) + SIZEOF(.carrier) <= 0x22cc, "carrier overlaps trampoline")
ASSERT(ADDR(.trampoline) == 0x22cc, "trampoline address changed")
ASSERT(ADDR(.trampoline) + SIZEOF(.trampoline) <= 0x2300, "trampoline overlaps IRQ")
