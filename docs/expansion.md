# Batch 2: four more stock leaves

Historical batch-2 preparation record. [That run is complete](../decomp/results/batch2-run-20261017/notes.md):
all four drafts are reviewed and independently rebuilt. Do not reclaim them or
repeat the old prompt below. The prior six drafts also remain reviewed.
Use [the broader workflow](broader-workflow.md) for current intake and batch 3.
Existing leaf pins remain unchanged.

| Task | Owned range, end exclusive | Main review concern |
| --- | --- | --- |
| `fn_00013f58` | `0x13f58..0x13f72`, 26 bytes | Six alternating byte loads/stores; overlap must retain original behavior. |
| `fn_00013f72` | `0x13f72..0x13f7a`, 8 bytes | Two byte stores; halfword argument and void return are hypotheses. |
| `fn_000154d4` | `0x154d4..0x154ea`, 22 bytes | Four byte reads; callers retain r3 across calls. Preserve exact register effects. |
| `fn_00018100` | `0x18100..0x18114`, 20 bytes | Zero/one predicate; unsigned comparison, unknown semantic names. |

The 76 bytes are assignment scope, **not matched coverage**. Original C types,
qualifiers and historical compiler remain hypotheses. No matching source was
precomputed for these workers. The unchanged ARMCC profile is supported by the
completed pilot and a new six-source regression rebuild, not a promise that
every new candidate will match within its attempt limit.

## Prepared evidence and limits

Each leaf has read-only Ghidra per-instruction TMode/flow evidence, original-byte
checks, an independent LLVM decode, incoming/outgoing references and caller
context. The coordinator reviewed exact boundaries, unique ownership, internal
branches and returns. No outgoing calls, literal pools, absolute globals or
stack use occur in these four bodies. Hidden indirect references are still
unknown. Do not infer whole-inventory approval from this limited review.

The [preparation report](../decomp/results/expansion-preparation/notes.md) records
hashes and controls. Local packets and the new leaf lock are under
`.decomp/evidence/next-leaves-v2/` and `.decomp/next-leaves-v2/`, respectively;
retain them alongside the prior ignored artifacts.
[The proposal snapshot](../decomp/proposals/batch-2-leaves.json) is preserved;
its four definitions were appended unchanged to [functions.json](../decomp/functions.json).
Do not regenerate or edit assigned task definitions to change scores.

Use [the existing guarded workflow](swarm.md): separate worktrees, at most two
Luna workers, coordinator-only serial builds, a complete diff audit, independent
source/ABI review and an unchanged-source rebuild. The runner exposes this
document read-only in addition to the prior selected instructions. Its CLI
permissions, authentication isolation and writable mounts are unchanged.
The runtime and preparation gate both reject tasks outside this batch.

## Historical run procedure — completed, do not rerun

After committing preparation, check local pins, queue and runner versions, then
obtain a fresh account reading. The existing dated window and 45%-remaining
stop are retained; this preparation does not assign a model run or renew a quota
window. A pause latch still requires an explicit user resume.

```sh
python3 tools/decomp.py check --local
```

```sh
python3 tools/decomp.py status
```

Historical pre-run state: six reviewed functions and four queued/unclaimed functions.
No task should be claimed until immediately before its worker launch.

The following is the completed run's archived prompt, not a new assignment:

```text
Create a Goal to coordinate batch 2 only: fn_00013f58, fn_00013f72, fn_000154d4 and fn_00018100. Read AGENTS.md, docs/expansion.md, docs/preparation.md, docs/swarm.md and decomp/prompts/coordinator.md. Check committed preparation, local pins, queue, runner versions and live quota before claims. Use at most two gpt-6-luna workers through tools/swarm_worker.py, not inherited-permission subagents; use gpt-6.1-sol only for a bounded escalation. Stop at 45% weekly usage remaining to preserve at least 40% for work. Fail closed on unavailable quota, honor PAUSED.json, and ask before resuming or starting a new quota window. Use tools/swarm_build.py for serial pinned compilation and independent unchanged-source rebuilds. Audit every full diff and independently review source, ABI, aliasing and register clobbers; exact-range bytes are not certification. Respect the 20-minute, eight-attempt and three-no-improvement limits. Continue until these four tasks are reviewed or evidence-backed blocked, or the reserve guard stops the run. Do not reclaim the completed six tasks, add tasks, enable the experimental call verifier, change pins, access hardware, commit or push.
```

The block ends above. The two call wrappers below are **not** part of that run.

## Direct-call extension: tested experiment, not worker-ready

Historical status below. The [broader preparation](broader-workflow.md) subsequently
qualified two stock call specimens and integrated trusted dispatch, callee
contracts and guarded batch admission without changing this experiment's pins.
The original two specimens are calibration, not worker assignments.

[armcc_calls.py](../tools/armcc_calls.py) is a separately locked experiment,
not a replacement for the leaf comparator. It allows explicitly declared
external Thumb functions, pins signatures and symbol addresses, checks original
BL destinations, permits only reviewed `R_ARM_THM_CALL` object relocations,
rejects offcut addends and verifies final linked destinations and complete load
bytes. It emits no callee stubs, masks no relocations and does not patch output.
It follows the [Arm ELF ABI's Thumb-call rules](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst),
checked 2026-10-16; actual compiler output is covered by local controls.

Two [wrapper candidates](../decomp/proposals/direct-call-candidates.json) have
reviewed body/call-site evidence and a separate experimental lock:
`fn_00006464` calls `fn_0001291c`; `fn_00006500` calls `fn_000134d4`.
Their callees modify global state that is not recovered by those wrappers.
Fixed external symbols are address bindings, not reconstructed dependencies.

Before any direct-call worker run: qualify the profile on stock call-bearing
code, review callee ABI/clobber assumptions, integrate the new scope into the
guarded queue/build handoff with negative tests, then issue separately reviewed
tasks and a user-assigned run. No direct-call task is active in the queue or
preparation gate. Synthetic controls do not establish stock-call calibration.

Shared globals/literal ownership, ARM/Thumb interworking, veneers, shared tails,
interrupts, MMIO and whole-image packaging remain unsupported by this experiment.
They need separate evidence/ownership and verifier extensions; do not silently
broaden its whitelist. Full reconstruction and hardware gates remain unchanged.
