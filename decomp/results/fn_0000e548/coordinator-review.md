# Coordinator review: fn_0000e548

Reviewed 2026-10-16 by coordinator-pilot-20261016, independently of the Luna
worker. This is the coordinator's review, not a claim that a second human or
review agent was engaged. Worker output remains a draft; queue acceptance is
reviewed, never certified matched.

## Source and ABI assessment

The C splits an unsigned 32-bit value into four byte stores at offsets zero through three. Right shifts by 8,16,24 are logical and defined; character narrowing retains each eight-bit field. The independently rebuilt output preserves store order at 0xe54a/0xe54c/0xe552/0xe554 and the original intermediate shifts, without memory reads or wider stores. Callers 0xbd5c and 0xc89a provide a pointer and word in r0/r1 and do not consume a return. Character access introduces no extra alignment or restrict assumption, and the pinned output leaves r0 unchanged.

All changed/untracked paths were audited against the task's allowed C file and
result directory. The final C contains no inline assembly, embedded instruction
arrays, compiler intrinsics, calls, globals, stubs, extra functions or post-link
patches. The worker received only selected instructions and its immutable packet,
not calibration C, compiler/licence state or the main checkout. The coordinator
supplied sanitized mismatch feedback where needed; the worker authored every
candidate source revision. No source was changed during independent review.

## Independent validation

- Final source SHA-256: `5f2296783f2d717bff5f0dc367862a81d24dfba86cb248b4ebea3d4b023df57b`.
- Pinned compiler-lock SHA-256: `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
- Fresh unchanged-source rebuild through `tools/swarm_build.py --review`:
  **16/16 bytes exact**, zero differing bytes, `certified_match: false`.
- Local comparison: `.decomp/swarm/builds/fn_0000e548/independent-review/comparison.json`.
- Comparison report SHA-256: `d9bae3aa7e1d8fd7edab7cdbbe61a0e443af1375cb0b9286a795866b5abe3bbf`.
- 1 ledger entries, 1 actual candidate compilations, one separate
  independent rebuild. 1 Luna turn(s), 40.797 measured worker-process
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
