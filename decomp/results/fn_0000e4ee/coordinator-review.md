# Coordinator review: fn_0000e4ee

Reviewed 2026-10-16 by coordinator-pilot-20261016, independently of the Luna
worker. This is the coordinator's review, not a claim that a second human or
review agent was engaged. Worker output remains a draft; queue acceptance is
reviewed, never certified matched.

## Source and ABI assessment

LDRB at 0xe4ee and 0xe4f0 reads offsets zero and one; the C uses unsigned-char access without an aligned halfword cast. Integer promotions in the shifted high byte reach at most 65280 and the sum at most 65535, so no signed overflow occurs. The unsigned-short conversion reproduces the narrowing at 0xe4f6/0xe4f8 and zero-extended return. Caller excerpts at 0x6aea onward use odd byte offsets; callers at 0x7a86 and 0xcb00 store halfwords, consistent with this candidate. The exact pinned output preserves both original byte loads and their order.

All changed/untracked paths were audited against the task's allowed C file and
result directory. The final C contains no inline assembly, embedded instruction
arrays, compiler intrinsics, calls, globals, stubs, extra functions or post-link
patches. The worker received only selected instructions and its immutable packet,
not calibration C, compiler/licence state or the main checkout. The coordinator
supplied sanitized mismatch feedback where needed; the worker authored every
candidate source revision. No source was changed during independent review.

## Independent validation

- Final source SHA-256: `fa3cd09f97502aaa03593bbf3ca7f7270f39d304b41493916a2dfb83e2f34df7`.
- Pinned compiler-lock SHA-256: `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
- Fresh unchanged-source rebuild through `tools/swarm_build.py --review`:
  **14/14 bytes exact**, zero differing bytes, `certified_match: false`.
- Local comparison: `.decomp/swarm/builds/fn_0000e4ee/independent-review/comparison.json`.
- Comparison report SHA-256: `f73fc18391e0c9f441c12e927fa9b782325abf790638c9375796c0669a57f119`.
- 2 ledger entries, 2 actual candidate compilations, one separate
  independent rebuild. 2 Luna turn(s), 51.271 measured worker-process
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
