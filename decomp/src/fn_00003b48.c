unsigned int fn_00003b48(unsigned int value, unsigned int offset)
{
    unsigned int adjusted;

    if (value == 0xf0000000u) {
        return 0u;
    }

    adjusted = value - offset;
    adjusted &= 0x0fffffffu;

    if (adjusted >= 0x08000000u) {
        return 1u;
    }

    return 0u;
}
