/* Synthetic fixture only: no Kensington code or constants. */
extern unsigned external_a(unsigned);
extern unsigned external_b(unsigned);
const unsigned table[4] = { 3, 5, 11, 17 };
volatile unsigned initialized = 0x13579bdfu;
volatile unsigned sink;

unsigned candidate(const unsigned char *input, unsigned i)
{
    unsigned value = (unsigned)(int)(signed char)*input + table[i & 3u] + 0x12345678u;
    sink = value;
    return external_a(value) + initialized;
}
