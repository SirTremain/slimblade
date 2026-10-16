/* Synthetic compiler-access check, not recovered firmware or calibration. */
unsigned int probe(unsigned int value)
{
    return (value * 3u) ^ 0x12345678u;
}
