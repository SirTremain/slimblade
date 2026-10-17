# Independent coordinator review

Reviewer: coordinator-batch3-20261017. Decision: reviewed draft, not a certified
match. Source SHA-256:
`231d95bbdfa41919cca3e728db1f273e1763df3570e1d0ece8c4ded7f1e1e455`.

## Source and ABI

Reviewed the immutable listing, LLVM decode, caller/callee context and frozen
call contract independently of the worker narrative. The ordinary C forwards
the pointer and both full-width unsigned integers without conversion or
dereference, preserves the external side-effecting call, discards its result,
then returns zero. There are no restrict/purity annotations, artificial
volatile accesses, pointer arithmetic, local object accesses, globals, asm,
intrinsics, stubs or embedded original code. No new aliasing or alignment
assumptions are imposed by the wrapper. Original declarations remain hypotheses.

The caller at 0x7916..0x791c sets r2=1, r1=0, r0=r4, and 0x7920 branches onward
without consuming r0. In both emitted ELFs, 0xbe60 pushes r4 and the incoming
return address, reducing SP by 8 and preserving its entry alignment. The BL at
0xbe62 forwards r0-r3 unchanged and targets Thumb entry 0xbd7c; r3 is incidentally
forwarded, not declared a fourth parameter. No scratch register is synthesized
by the wrapper. At 0xbe66 MOVS clears r0 and sets N/Z; C/V are not overwritten
by that instruction. POP at 0xbe68 restores r4 and SP and loads the saved return
address into PC. LR is a call-clobbered register, not promised restored as a
register value. There is no veneer, shared tail, literal pool or owned data.

The callee saves r4-r7 and LR, allocates another 20 bytes, and restores that
frame at 0xbe56..0xbe58. It compares full r1 at 0xbd92 and r2 at 0xbd9a, then
stores the low byte of r2 at 0xbd9c. Object reads/writes include 0xbd84,
0xbd88, 0xbe46 and 0xbe4e; a global is read via the literal at 0xbe5c and
further calls occur. Its r0-r3/flag effects and transitive scratch effects are
not narrowed to an invented purity or clobber contract. The wrapper changes
only its observed stack operations and final r0/NZ beyond those effects;
the exact emitted instruction sequence preserves their pass-through behavior.
Full callee types, aliasing/MMIO semantics and transitive effects remain
unreconstructed. Fixed symbol binding supplies no callee implementation.

## Build and complete diff audit

The complete worktree status contained only the assigned source, notes and
result.json. All three were read; the tracked-file diff was empty and there
were no out-of-assignment changes. A failed worker delete/add edit did not
alter the assignment boundary; the final ordinary-C update was inspected.

One candidate compile and one fresh unchanged-source `--review` build through
`tools/swarm_build.py` each reproduced all 10 owned bytes with no differences.
Both ELFs were independently disassembled and their stack, register and BL
behavior checked above. Source hash was identical before/after review and
integration; no worker objects were reused. Evidence is retained under
`.decomp/swarm/builds/fn_0000be60/attempt-01/` and `independent-review/`.
Pins, flags, ranges, expected bytes and external contracts were unchanged.
All 154 offline tests passed, including negative verifier controls; the pinned
preparation's real compiler qualification was verified, not rerun with new flags.

This accepts only the reviewed wrapper draft. It does not reconstruct its
callees, identify the original compiler or certify whole-image equivalence.
Matching coverage is unknown and hardware gates remain closed.
