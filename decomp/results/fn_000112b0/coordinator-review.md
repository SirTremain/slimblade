# Independent coordinator review — terminal blocked

Reviewer: coordinator-batch3-20261017. Decision: terminal block, not reviewed
acceptance or match certification. Source SHA-256:
`52a25180e6f144708e43b08c1b68aeadefa8c8730682f92769fc3d744ff33807`.

## Independent source, ABI and effects review

The C uses the frozen void(void) wrapper and void(unsigned int) external
prototype and calls fn_0000e58c with the full-width constant zero. It has no
local memory accesses, aliasing assumptions, invented qualifiers, globals,
inline asm, stubs or artificial side effects. The caller at 0x10a2a reloads
r0 at 0x10a2e; that supports an ignored result but does not prove the original
declaration. Void source is not a guarantee about actual outgoing register bits.

Compared the candidate ELF disassembly independently with the immutable
instructions and caller/callee context. Candidate MOVS r0,#0 at 0x112b0 is
followed by PUSH {r4,lr} at 0x112b2; stock has those instructions reversed.
The original and candidate BL are both at 0x112b4, targeting Thumb 0xe58c,
and POP {r4,pc} is at 0x112b8. The candidate therefore differs at four byte
positions in the first four bytes. It is not an exact reconstruction despite
the same observed call argument and call boundary. In particular, instruction
order and intermediate register/SP state must not be waived as irrelevant.

Both sequences subtract 8 from SP before the call and restore r4/SP and the
saved return PC afterwards; LR itself is call-clobbered. They leave r1-r3
unchanged before the call. Callee 0xe58c saves r4/LR and calls 0x6008; that leaf
uses r0/r1/r2 and flags, not r3, and has no further calls. It reads mode byte
0x40011d and, for modes 2/3 with zero input, clears word 0x400124 at 0x6024.
It returns r0=0 for the wrapper's input. Callee 0xe592 loads r1=0x400514 and
0xe594 stores the returned byte at 0x400515 without changing r0. These actual
register/memory effects were inspected, not inferred solely from generic
caller-clobbered allowances. Globals, qualifiers and callee implementations
remain outside this assignment; fixed external symbols do not reconstruct them.

## Block evidence and limits

Attempt 1 through the serial guarded build completed with a four-byte mismatch,
correct call relocation at offset 4, and the source hash above. Sanitized
feedback was supplied to a second isolated Luna turn. It left source unchanged
and wrote an evidence-backed blocked report; the supervisor subsequently
stopped the process at the original 20-minute claim deadline. The checkpoint
records `ValueError: worker time limit`. No fresh candidate, second compile,
independent exact-source rebuild or escalation was made. The review-build guard
requires an unchanged exact candidate, which this task does not have.

The initial quota pause consumed most of the wall-clock allowance. Resume did
not reset the original claim at 2026-10-17T00:23:26.433044Z or its deadline at
00:43:26.433044Z. This is an instruction-scheduling mismatch plus an exhausted
assigned time budget, not evidence that matching is impossible. There is no
justification for inserting artificial accesses, changing signatures/flags,
patching output, releasing/reclaiming or granting extra attempts in this run.

Full worktree audit found only assigned source, notes and result.json; all
contents and the empty tracked-file diff were reviewed after the process stopped.
Raw events/checkpoints, comparison and attempt ledger remain ignored under
`.decomp/swarm/`. Worker model/timing fields are self-report; runner invocation
establishes gpt-6-luna. The integrated result adds coordinator attribution.
All 154 offline tests passed. Submit the blocked report and use review decision
`block`; any later retry requires a separate explicit scope/budget and deliberate
queue reconciliation. No automatic retry is implied.
