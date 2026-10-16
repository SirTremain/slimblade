# `fn_00003bb4` draft

## Observations

- Range `0x3bb4`–`0x3bbd` is ten bytes of Thumb code, ending with `bx lr`.
- At `0x3bb4`, `lsl r1,r1,#1` doubles the second 32-bit argument modulo 2^32.
- At `0x3bb6`, `add r0,r1,r0` adds it to the first argument modulo 2^32.
- `lsl r0,r0,#4` at `0x3bb8`, followed by logical `lsr r0,r0,#4` at `0x3bba`, retains bits 0–27 (mask `0x0fffffff`).
- Caller `0xd51c` calls the entry and stores returned `r0` at `0xd520`. It loads a halfword at `0xd516`, shifts it left once into `r1`, and sets `r0` from `r7` before the call.
- No outgoing references, loads, stores, literal pool or absolute address occur in the bounded body. Evidence packet also notes no discovered offcut references; hidden indirect callers remain unresolved.

## Inference and uncertainty

Unsigned 32-bit parameters and return are consistent with the packet signature and make the logical truncation explicit. The proposed expression is `(arg0 + (arg1 << 1)) & 0x0fffffff`. Names and the original declaration are unknown. The caller supports the register-level argument flow but does not independently prove source types or original compiler ABI. The task's AAPCS signature remains a hypothesis for coordinator review.

## Validation

No compiler/comparison was run. This is a source draft only; no match is claimed. Evidence: `/evidence/instructions.json`, `listing.txt`, `llvm.txt`, `references.json`, and `callers.txt` (packet files are immutable inputs).
