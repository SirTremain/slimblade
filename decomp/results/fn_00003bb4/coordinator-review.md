# Coordinator review: fn_00003bb4

Reviewed 2026-10-16 by coordinator-pilot-20261016, independently of the Luna
worker. This is the coordinator's review, not a claim that a second human or
review agent was engaged. Worker output remains a draft; queue acceptance is
reviewed, never certified matched.

## Source and ABI assessment

The unsigned shift at 0x3bb4 and addition at 0x3bb6 are defined modulo 2^32 in the C. Masking with 0x0fffffff implements the logical left/right shifts at 0x3bb8/0x3bba for every input bit pattern. The caller at 0xd51c supplies r0/r1 and stores r0 at 0xd520. Its own earlier doubling of a loaded halfword is separate from this function's doubling and is not folded away. No memory/stack operations or callee-saved clobbers are introduced.

All changed/untracked paths were audited against the task's allowed C file and
result directory. The final C contains no inline assembly, embedded instruction
arrays, compiler intrinsics, calls, globals, stubs, extra functions or post-link
patches. The worker received only selected instructions and its immutable packet,
not calibration C, compiler/licence state or the main checkout. The coordinator
supplied sanitized mismatch feedback where needed; the worker authored every
candidate source revision. No source was changed during independent review.

## Independent validation

- Final source SHA-256: `cf4e715e4ade8788e360cb410aed1f08530415d7f1699f3de50a261a900ed761`.
- Pinned compiler-lock SHA-256: `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
- Fresh unchanged-source rebuild through `tools/swarm_build.py --review`:
  **10/10 bytes exact**, zero differing bytes, `certified_match: false`.
- Local comparison: `.decomp/swarm/builds/fn_00003bb4/independent-review/comparison.json`.
- Comparison report SHA-256: `ec8c2d28bd4683a9cf1a3da83ebae9622abd2e41bcca315a27155283ec183c4a`.
- 1 ledger entries, 1 actual candidate compilations, one separate
  independent rebuild. 1 Luna turn(s), 32.698 measured worker-process
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
