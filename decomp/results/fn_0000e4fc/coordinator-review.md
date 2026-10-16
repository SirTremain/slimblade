# Coordinator review: fn_0000e4fc

Reviewed 2026-10-16 by coordinator-pilot-20261016, independently of the Luna
worker. This is the coordinator's review, not a claim that a second human or
review agent was engaged. Worker output remains a draft; queue acceptance is
reviewed, never certified matched.

## Source and ABI assessment

The two-pair unsigned sum implements ADDs at 0xe502, 0xe50c and 0xe50e. Each byte is widened to unsigned int before shifting; shifts by 8/16/24 are defined and all four fields are disjoint. The result is the complete 32-bit little-endian value, with no signed high-byte overflow. Although the C declaration alone does not enforce volatile ordering, the independently rebuilt pinned output has the original LDRB order 1,0,2,3 at 0xe4fc/0xe4fe/0xe504/0xe506 and no stack operations. Caller 0xc70c consumes r0 at 0xc710, consistent with a 32-bit return.

All changed/untracked paths were audited against the task's allowed C file and
result directory. The final C contains no inline assembly, embedded instruction
arrays, compiler intrinsics, calls, globals, stubs, extra functions or post-link
patches. The worker received only selected instructions and its immutable packet,
not calibration C, compiler/licence state or the main checkout. The coordinator
supplied sanitized mismatch feedback where needed; the worker authored every
candidate source revision. No source was changed during independent review.

## Independent validation

- Final source SHA-256: `a2b085380d684e837095c480f2d84216da7a30cac03542e604962fd55a816764`.
- Pinned compiler-lock SHA-256: `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
- Fresh unchanged-source rebuild through `tools/swarm_build.py --review`:
  **22/22 bytes exact**, zero differing bytes, `certified_match: false`.
- Local comparison: `.decomp/swarm/builds/fn_0000e4fc/independent-review/comparison.json`.
- Comparison report SHA-256: `04f170ba02ee3f0bc07e35f01f254a4608465e1b9e907b4ff529470847197956`.
- 2 ledger entries, 2 actual candidate compilations, one separate
  independent rebuild. 2 Luna turn(s), 92.103 measured worker-process
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
