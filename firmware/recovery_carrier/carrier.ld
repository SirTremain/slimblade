OUTPUT_ARCH(arm)
ENTRY(carrier_dispatch)

MEMORY
{
    CARRIER (rx) : ORIGIN = 0x000021ac, LENGTH = 0x00000154
}

SECTIONS
{
    .text :
    {
        *(.text .text.*)
        *(.rodata .rodata.*)
    } > CARRIER

    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
        *(.comment)
    }
}

ASSERT(ADDR(.text) == 0x21ac, "carrier must start at 0x21ac")
ASSERT(ADDR(.text) + SIZEOF(.text) <= 0x2300, "carrier overlaps stock IRQ code")
