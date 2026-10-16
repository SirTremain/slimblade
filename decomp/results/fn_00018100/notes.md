# fn_00018100 draft

## Evidence and interpretation

Owned range: `0x00018100..0x00018114` (20 bytes), Thumb state. At `0x18100`, `cmp r0,#0` followed by `bne 0x18110` sends every nonzero first argument to the one return. With zero in `r0`, `mov r0,#1; lsl r0,r0,#11` forms `0x800`. `cmp r1,r0; bcs 0x18110` uses unsigned higher-or-same semantics, so `r1 >= 0x800` returns one. Otherwise `mov r0,#0; bx lr` returns zero. The common path at `0x18110` returns one.

This supports the source predicate `arg0 == 0U && arg1 < 0x800U`. The listing bytes are corroborated by the independent LLVM disassembly and instruction-flow packet. Incoming call references are `0x175d4` and `0x177fe`; both callers check `r0` against zero after return. The body has no calls, globals, literal data, stack operations, or internal references outside the owned range. Semantic argument names and the original declaration remain unknown.

## Candidate

`decomp/src/fn_00018100.c` expresses the predicate with the assigned unsigned-int signature and ordinary C. No assembly, intrinsic, or padding is included.

## Validation and handoff

No compiler attempt was run by this worker. The candidate is a draft and has not been byte-compared or certified. Request coordinator compilation and source/ABI review; use a fresh attempt output directory.
