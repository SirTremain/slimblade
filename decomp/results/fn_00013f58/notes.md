# `fn_00013f58` draft

## Observed evidence

- The owned Thumb range is `0x00013f58..0x00013f72` (26 bytes). At `0x13f58` through `0x13f6e`, instructions alternate `LDRB` from `r1 + n` and `STRB` to `r0 + n`, for `n = 0..5`; `0x13f70` is `BX LR`. Each instruction is 2 bytes. The packet's LLVM disassembly independently decodes the same bytes.
- Packet references show callers at `0x00004ff2` and `0x000055e6`, both targeting the entry. No outgoing references, literals, globals, calls, or stack accesses are listed. The packet notes that callers do not consume a return value.
- The source keeps six byte assignments in the observed order. This preserves effects when source and destination overlap; it does not add `restrict`, wider accesses, or a library copy.

## Inferences and unresolved points

- A six-byte copy with destination in `r0` and source in `r1` is directly supported by the loads/stores. `void (unsigned char *, const unsigned char *)` is the assigned signature hypothesis, not independently established source/ABI truth.
- The final load overwrites `r1`, while prior loads use `r2`; the C draft leaves exact register allocation/clobbers to the compiler. Source declaration details and historical compiler provenance remain unresolved.
- Hidden indirect callers are unknown. The packet's boundary review and local cross-check support this owned range but do not approve broader inventory boundaries.

## Validation

- Read task packet under `/evidence` and reviewed the addressed Ghidra listing, caller context, reference list, metadata, and LLVM disassembly.
- No compiler or comparator was run in the worker, as required by the enforced handoff. No exact-range match is verified. Request a coordinator ARMCC5 build and redacted feedback.
