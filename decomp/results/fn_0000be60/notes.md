# fn_0000be60 draft

## Observed

- At `0x0000be60`, bytes `10 b5` save `r4` and `lr`.
- At `0x0000be62`, bytes `ff f7 8b ff` issue a Thumb `BL` to `0x0000bd7c`.
  No argument-register setup occurs between entry and the call, so incoming
  `r0`, `r1`, and `r2` are forwarded unchanged.
- At `0x0000be66`, bytes `00 20` set `r0` to zero, discarding the callee return.
- At `0x0000be68`, bytes `10 bd` restore `r4` and return via restored `lr`.
  The owned range ends at `0x0000be6a`; packet data identifies no literals or
  data in the range.
- The caller at `0x0000791c` sets `r0=r4`, `r1=0`, `r2=1` before the call and
  branches onward without consuming the result.
- The callee listing at `0x0000bd7c` uses the incoming pointer for byte/word
  field accesses and may call other routines and access a global at `0x0000be5c`.
  Its side effects therefore cannot be removed just because this wrapper returns
  zero.

## Inference and unresolved details

- The draft uses the assignment's pinned declaration
  `unsigned int fn_0000bd7c(unsigned char *, unsigned int, unsigned int)` and
  the assigned wrapper signature. Original source declarations, structure
  identity, and wider caller/ABI usage remain hypotheses.
- The push/pop preserve `r4` and `lr`; as an ordinary call, the callee may change
  caller-clobbered registers. Exact compiler output and full source/ABI review
  have not been performed.

## Validation

- Manually cross-checked instruction bytes and control flow against
  `/evidence/listing.txt`, `/evidence/instructions.json`, and the LLVM listing
  in `/evidence/llvm.txt`; reviewed caller/callee context in the packet.
- No compiler or comparator was run. No exact-range match is claimed. Coordinator
  compilation and independent source/ABI review are pending.
