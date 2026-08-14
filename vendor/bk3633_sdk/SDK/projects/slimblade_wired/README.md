# SlimBlade wired BK3635 port

This BK3635-specific project is the controlled starting point for a wired-only
SlimBlade firmware. It currently rebuilds the stock v4.49 ARM vector/startup
region at `0x2020`--`0x21ab` and IRQ/FIQ wrappers at `0x2300`--`0x232f`; it is
not a complete or flashable image.

The assembly is readable source derived from the Apache-2.0 BK3633 startup
structure and independent SlimBlade disassembly. `make preflight` requires the
generated startup and interrupt-wrapper bytes to equal hash-locked stock v4.49
regions exactly.

Requirements: Clang/LLD, LLVM objcopy, Python 3, and the official v4.49 image at
`/tmp/slimblade-v449.bin` (or pass `STOCK=/path/to/image`). Generated files stay
under ignored `build/`.
