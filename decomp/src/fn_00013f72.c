void fn_00013f72(unsigned char *destination, unsigned short value)
{
    destination[0] = (unsigned char)value;
    destination[1] = (unsigned char)(value >> 8);
}
