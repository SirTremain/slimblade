# fn_000112b0 worker report

**Status: blocked.** No source change is proposed. The task-owned C still expresses the observed no-argument `void` wrapper calling `fn_0000e58c(0u)`.

## Evidence

- `/evidence/listing.txt` and `/evidence/instructions.json`: range `0x000112b0..0x000112ba`, Thumb state. Original instruction order is `PUSH {r4,lr}` at `0x112b0`, `MOVS r0,#0` at `0x112b2`, `BL 0x0000e58c` at `0x112b4`, and `POP {r4,pc}` at `0x112b8`.
- `/evidence/references.json`: direct incoming call at `0x00010a2a` and outgoing call at `0x000112b4`. `/evidence/context.md` states the caller ignores this wrapper's return.
- `/evidence/callee-instructions.json`: callee `0x0000e58c` is a separate Thumb body; its packet contract is `void(unsigned int)`. Its implementation and transitive side effects remain external dependencies.
- Coordinator feedback for attempt 1: compiled candidate emitted `MOVS` before `PUSH`, differed in four of ten bytes, and had the correct BL relocation at offset 4. No source, ABI, or call change is indicated by this feedback.

## Decision and validation

The ordering mismatch is compiler scheduling. The body evidence does not establish a local variable, state access, or other ordinary-C side effect that could legitimately constrain the constant setup to occur after the prologue. Adding artificial state or side effects would be unsupported. Therefore no new candidate is submitted and the scheduling mismatch is the blocker, consistent with the coordinator's bounded-turn instruction.

No compiler command was run in this worker turn, per the enforced runner handoff. An exact-range match was not verified, and this report does not claim certification. See `result.json` for the structured report.
