/* New BK3635 SlimBlade linker script; see startup_stock_reference.S. */
OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(stock_vectors)

MEMORY
{
    STARTUP (rx) : ORIGIN = 0x00002020, LENGTH = 0x18c
    IRQ     (rx) : ORIGIN = 0x00002300, LENGTH = 0x010
    FIQ     (rx) : ORIGIN = 0x00002320, LENGTH = 0x010
}

SECTIONS
{
    .startup 0x00002020 :
    {
        KEEP(*(.startup))
    } > STARTUP

    .irq_wrapper 0x00002300 :
    {
        KEEP(*(.irq_wrapper))
    } > IRQ

    .fiq_wrapper 0x00002320 :
    {
        KEEP(*(.fiq_wrapper))
    } > FIQ

    /DISCARD/ :
    {
        *(.ARM.attributes)
        *(.comment)
        *(.note*)
    }
}

ASSERT(ADDR(.startup) == 0x2020, "startup address changed")
ASSERT(SIZEOF(.startup) == 0x18c, "startup size changed")
ASSERT(ADDR(.irq_wrapper) == 0x2300, "IRQ wrapper address changed")
ASSERT(SIZEOF(.irq_wrapper) == 0x10, "IRQ wrapper size changed")
ASSERT(ADDR(.fiq_wrapper) == 0x2320, "FIQ wrapper address changed")
ASSERT(SIZEOF(.fiq_wrapper) == 0x10, "FIQ wrapper size changed")
