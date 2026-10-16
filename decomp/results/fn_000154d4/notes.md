# `fn_000154d4` draft

## Observed

- Entry `0x154d4`, Thumb; owned range `0x154d4..0x154ea` (22 bytes).
- `0x154d4..0x154e6` reads one byte from `r0 + 1`, `r0`, `r0 + 2`, and `r0 + 3`, then combines them as bits 8–15, 0–7, 16–23, and 24–31 in `r0`. Every load is `LDRB` (zero extending). `0x154e8` returns with `BX LR`.
- Listing and independent LLVM decode agree on all 11 instructions; packet range SHA-256 is `627c59a19dec894d2b05a7be29b415f545c96f65d3690d9f8aed1b7fb34dffc5`.
- Eight discovered calls enter at the function start from `0x17c36`, `0x17c40`, `0x17c4a`, `0x17c54`, `0x17c60`, `0x17c6a`, `0x17c74`, and `0x17c7e`. No outgoing references are recorded.

## Draft and ABI questions

The C expression assembles the observed little-endian 32-bit value. Explicit casts to `unsigned int` before shifting avoid signed-shift behavior at bit 31. `const` expresses that the body only reads through its argument; it does not establish the original source qualifier. Neither pointer alignment nor volatile access is evidenced.

All instructions write only `r0`, `r1`, and `r2`; the function makes no stack adjustment or call and leaves `r3` unchanged. The callers around `0x17c60..0x17c7e` rely on `r3` after calls, so the pinned compiler output must retain that exact clobber behavior. Source declaration and historical compiler remain hypotheses.

## Validation

Coordinator feedback: attempts 1 and 2 produced identical machine code (24 bytes, 12 differing bytes). Attempt 3 improved to 22 bytes with 5 differing bytes; all differences are in the first three instructions, while `0x154da..0x154e8` matches. Coordinator correction: attempt 3 loads byte 1, shifts it, then loads byte 0; the original loads byte 1, loads byte 0, then shifts. The revised C initializes `value` with byte 0, then accumulates shifted bytes 1, 2 and 3. This source order is not the original machine access order; nonvolatile loads may be scheduled by the compiler. Actual output must be checked. Unsigned widening avoids signed-shift overflow. No compilation was run by the worker; the coordinator's final source/ABI and rebuild findings are recorded separately in coordinator-review.md. No certified match is claimed.
