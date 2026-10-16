unsigned int fn_0000e4fc(const unsigned char *bytes)
{
    unsigned int low = (unsigned int)bytes[0] +
                       ((unsigned int)bytes[1] << 8);
    unsigned int high = ((unsigned int)bytes[2] << 16) +
                        ((unsigned int)bytes[3] << 24);

    return low + high;
}
