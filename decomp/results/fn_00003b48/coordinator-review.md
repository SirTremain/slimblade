# Coordinator review: fn_00003b48

Reviewed 2026-10-16 by coordinator-pilot-20261016, independently of the Luna
worker. This is the coordinator's review, not a claim that a second human or
review agent was engaged. Worker output remains a draft; queue acceptance is
reviewed, never certified matched.

## Source and ABI assessment

At 0x3b4c/0x3b4e the equality check is specifically against 0xf0000000, not any value with that top nibble. The C preserves that sentinel before subtraction. Unsigned subtraction at 0x3b50 wraps modulo 2^32; masking at 0x3b54 retains 28 bits. The unsigned threshold at 0x3b58/0x3b5a distinguishes values below 0x08000000; the revised positive branch returns one and the other paths return zero. All 17 recorded caller excerpts compare r0 to zero after the call; the r0/r1 argument and r0 result convention is consistent. No memory, stack, callee-saved register or external dependency is introduced.

All changed/untracked paths were audited against the task's allowed C file and
result directory. The final C contains no inline assembly, embedded instruction
arrays, compiler intrinsics, calls, globals, stubs, extra functions or post-link
patches. The worker received only selected instructions and its immutable packet,
not calibration C, compiler/licence state or the main checkout. The coordinator
supplied sanitized mismatch feedback where needed; the worker authored every
candidate source revision. No source was changed during independent review.

## Independent validation

- Final source SHA-256: `c104e5ef2dd2a9b3c035e1cc779fdab6e06089c9819279f26ea8c2ab6fc65854`.
- Pinned compiler-lock SHA-256: `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
- Fresh unchanged-source rebuild through `tools/swarm_build.py --review`:
  **28/28 bytes exact**, zero differing bytes, `certified_match: false`.
- Local comparison: `.decomp/swarm/builds/fn_00003b48/independent-review/comparison.json`.
- Comparison report SHA-256: `10bd4de4cb681abb1073d68b556fb856e684d9a614a1d5b3cfc2bb3434e3e693`.
- 3 ledger entries, 2 actual candidate compilations, one separate
  independent rebuild. 2 Luna turn(s), 60.280 measured worker-process
  seconds. These do not reset or replace the cumulative queue-claim deadline.
- All 123 offline tests passed. Local packet/tool pins passed. The existing
  seven-control compiler report was hash-checked unchanged; it was not rerun
  or presented as new control execution in this pilot.

Original worker metadata and its statements that coordinator validation was
pending are retained as the worker-stage snapshot. The added coordinator review
records subsequent results; launch/checkpoint/ledger records override generic
model names or unmeasured elapsed-time fields in that snapshot.

## Limits retained

The pinned signature is supported as a candidate by register use and inspected
callers, not proven as the original C declaration. Const/volatile qualifiers,
semantic names, historical compiler provenance and hidden indirect callers are
not recovered by byte equality. Pointer tasks require valid byte-addressed
storage; no claim about all MMIO domains or future compiler transformations is
made. ARM/Thumb state, original widths, side effects and instruction ordering
are preserved in this fixed independently rebuilt range. No flags are declared
as source return values; sampled caller use does not contradict the candidate
AAPCS convention. This accepts only the scoped draft, not certified source/ABI
equivalence, whole-image equivalence, or hardware safety. Matching coverage is
unknown. See [the run report](../pilot-run-20261016/notes.md).
