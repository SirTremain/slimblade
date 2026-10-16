# Coordinator review: fn_0000e540

Reviewed 2026-10-16 by coordinator-pilot-20261016, independently of the Luna
worker. This is the coordinator's review, not a claim that a second human or
review agent was engaged. Worker output remains a draft; queue acceptance is
reviewed, never certified matched.

## Source and ABI assessment

The two character stores preserve offsets zero then one at 0xe540/0xe544. Unsigned-short promotion followed by >>8 is nonnegative and within int range; narrowing to unsigned char writes only bits 0..7 and 8..15. No alignment or restrict assumptions are introduced. Caller 0x44e2 loads a halfword into r1 and points r0 at the destination; calls at 0x44ee/0x450c use odd destination offsets. Reviewed callers overwrite or ignore r0 afterward, consistent with void but not proof of the original declaration. The pinned output preserves r0 and exactly two byte stores.

All changed/untracked paths were audited against the task's allowed C file and
result directory. The final C contains no inline assembly, embedded instruction
arrays, compiler intrinsics, calls, globals, stubs, extra functions or post-link
patches. The worker received only selected instructions and its immutable packet,
not calibration C, compiler/licence state or the main checkout. The coordinator
supplied sanitized mismatch feedback where needed; the worker authored every
candidate source revision. No source was changed during independent review.

## Independent validation

- Final source SHA-256: `502d696eb3678092e1739fb5af57465d52725a291b94b0448ef260bd33c8ea49`.
- Pinned compiler-lock SHA-256: `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
- Fresh unchanged-source rebuild through `tools/swarm_build.py --review`:
  **8/8 bytes exact**, zero differing bytes, `certified_match: false`.
- Local comparison: `.decomp/swarm/builds/fn_0000e540/independent-review/comparison.json`.
- Comparison report SHA-256: `3cb22e593bef4ae2eda0b49a79d2a68b84df135221aa71e8bcb31260733d3597`.
- 1 ledger entries, 1 actual candidate compilations, one separate
  independent rebuild. 1 Luna turn(s), 47.620 measured worker-process
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
