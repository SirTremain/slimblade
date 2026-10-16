unsigned int fn_000154d4(const unsigned char *bytes)
{
    unsigned int value = (unsigned int)bytes[0];
    value |= (unsigned int)bytes[1] << 8;
    value |= (unsigned int)bytes[2] << 16;
    value |= (unsigned int)bytes[3] << 24;
    return value;
}
