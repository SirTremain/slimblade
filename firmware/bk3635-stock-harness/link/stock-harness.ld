OUTPUT_ARCH(arm)
ENTRY(startup_trampoline)

MEMORY
{
    CARRIER (rx) : ORIGIN = 0x000021ac, LENGTH = 0x00000120
    TRAMPOLINE (rx) : ORIGIN = 0x000022cc, LENGTH = 0x00000034
    CUSTOM_RUNTIME (rx) : ORIGIN = 0x0001c460, LENGTH = 0x0000012c
    SENSOR_HOOK (rx) : ORIGIN = 0x0001c5c0, LENGTH = 0x00000020
    SENSOR_SUPPORT (rx) : ORIGIN = 0x0001c5e0, LENGTH = 0x00000100
}

SECTIONS
{
    .carrier 0x000021ac :
    {
        KEEP(*(.text.carrier))
    } > CARRIER

    .probe 0x000022c0 :
    {
        KEEP(*(.text.rust_probe))
    } > CARRIER

    .trampoline 0x000022cc :
    {
        KEEP(*(.text.trampoline))
    } > TRAMPOLINE

    .custom_runtime 0x0001c460 :
    {
        KEEP(*(.text.custom_runtime))
    } > CUSTOM_RUNTIME

    .sensor_hook 0x0001c5c0 :
    {
        KEEP(*(.text.sensor_hook))
    } > SENSOR_HOOK

    .sensor_support 0x0001c5e0 :
    {
        KEEP(*(.text.sensor_support))
    } > SENSOR_SUPPORT

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
ASSERT(ADDR(.probe) == 0x22c0, "probe address changed")
ASSERT(ADDR(.probe) + SIZEOF(.probe) <= 0x22cc, "probe overlaps trampoline")
ASSERT(ADDR(.trampoline) == 0x22cc, "trampoline address changed")
ASSERT(ADDR(.trampoline) + SIZEOF(.trampoline) <= 0x2300, "trampoline overlaps IRQ")
ASSERT(ADDR(.custom_runtime) == 0x1c460, "custom runtime address changed")
ASSERT(ADDR(.custom_runtime) + SIZEOF(.custom_runtime) <= 0x1c58c,
       "custom runtime overlaps stock initializer literals")
ASSERT(ADDR(.sensor_hook) == 0x1c5c0, "sensor hook address changed")
ASSERT(ADDR(.sensor_hook) + SIZEOF(.sensor_hook) <= 0x1c5e0,
       "sensor hook exceeds replaced wireless-mode entry")
ASSERT(ADDR(.sensor_support) == 0x1c5e0, "sensor support address changed")
ASSERT(ADDR(.sensor_support) + SIZEOF(.sensor_support) <= 0x1c6e0,
       "sensor support exceeds reclaimed wireless-mode code")
