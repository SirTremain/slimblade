# Batch 4: Rea-assisted leaf reconstruction

Preparation date: 2026-10-17. Selected and locally validated, **not launched**.
The previous runs are terminal: eleven reviewed drafts and fn_000112b0 blocked.
Do not reclaim them. This batch contains three new assignments, 94 owned bytes,
using the unchanged `armcc5-leaf-feedback-v1` comparator and compiler options.

| Assignment | Owned range (end exclusive) | Review focus |
| --- | --- | --- |
| fn_00009fe2 | 0x9fe2–0xa012, 48 bytes | Unsigned branch conditions, narrowing, returned value; r2/r3 preserved |
| fn_00011e38 | 0x11e38–0x11e48, 16 bytes | Four ordered byte stores; caller-live r3 must remain unchanged |
| fn_00015e0c | 0x15e0c–0x15e2a, 30 bytes | Full-width logical shifts, internal control flow, preserved r3 |

Signatures are reviewed hypotheses, not recovered original declarations. The
byte-store helper duplicates the instruction bytes of reviewed fn_0000e548;
that fact is disclosed in its packet. Its different callers still require
independent ABI/clobber review. This is not presented as a fresh algorithm discovery.

## Rea's role

The [Rea adapter](rea.md) supplied instruction text, pseudocode, references,
control-flow and value-flow context. Complete upstream responses and caveats
are retained inside each immutable packet, alongside a source-report/profile
identity. Pseudocode is unverified analysis, not precomputed candidate C.

The coordinator separately checked original bytes, fresh per-instruction Thumb
state/flow, unique ownership, incoming entry-only references, caller use and
LLVM decoding. Rea range ends are inclusive; task ends are exclusive. The two
register-only functions have conditional and unconditional branches wholly
inside their bodies. The new intake checker handles those internal branches;
no comparator, compiler flag, AST rule or byte-comparison rule changed.

There are no calls, stack accesses, literal pools, fixed-address globals or
shared tails in the three owned bodies. The packet's pointer-store helper is
restricted to the incoming pointer and byte stores; fixed-address construction
must not be mistaken for a register-only leaf. Nearby fn_00015724 was excluded
for fixed-address word writes, and fn_000178dc for escaping control flow.
The existing call calibration specimens and blocked batch-3 task remain excluded.

## Frozen preparation

- [Selection and addressed review](../decomp/proposals/batch-4-selection.json).
- [Complete task proposal](../decomp/proposals/batch-4-leaves.json), integrated
  without changing any earlier task definition.
- [Batch manifest](../decomp/batches/batch-4-rea-leaves.json), SHA-256
  `6a1bd6fc1496515aecf8c4db7da847489979e48278b2de8ce17df68de770566c`.
- New local lock `.decomp/rea-batch4-v2/lock.json`, SHA-256
  `16c0d91990135f1012122072e5e41514d3100108abcee7c34fcab4c951944703`.
- Immutable packets under `.decomp/evidence/rea-batch4-v2/`, with full packet
  hashes in each assignment. Do not regenerate or modify them after admission.
- [Existing qualification evidence](../decomp/results/batch4-preparation/qualification.json)
  binds the earlier synthetic negative/repeat controls and ten stock-leaf
  regressions. Local admission verifies the new lock uses the same qualified
  code, tools, libraries, baseline and options. No new candidate was compiled
  during preparation; matching any of these three bodies is not guaranteed.

The preparation gate and policy select only these three IDs. All reserve,
window, concurrency and attempt limits are unchanged. The original ledger and
all earlier locks/packets remain intact. The [preparation report](../decomp/results/batch4-preparation/notes.md)
records checks and remaining limitations.

## Next run

Review and commit the preparation before creating worker worktrees. Keep ignored
local artifacts: a Git checkout alone does not contain the compiler, firmware,
evidence packets or corrected Ghidra database. No commit or push is performed
by preparation.

Run this read-only batch check:

```sh
python3 tools/reconstruction.py --batch decomp/batches/batch-4-rea-leaves.json --sha256 6a1bd6fc1496515aecf8c4db7da847489979e48278b2de8ce17df68de770566c --local
```

Then assign a bounded run for **fn_00009fe2, fn_00011e38 and fn_00015e0c only**,
using [the coordinator instructions](../decomp/prompts/coordinator.md).
Immediately before claims, the coordinator must verify committed preparation,
queue, local pins, runner versions, live quota, the existing window and any pause.
Do not interpret an old quota reading as current or automatically renew a window.
No worker/model job is requested by this preparation document.

Use at most two gpt-6-luna workers through `tools/swarm_worker.py`, with only a
bounded gpt-6.1-sol escalation inside an assigned budget. Stop at 45% weekly
remaining to retain at least 40% for work, fail closed on unavailable quota and
ask before resuming or starting another window. Serial compilation and fresh
unchanged-source review rebuilds go through `tools/swarm_build.py`. Preserve
20 minutes, eight attempts and three non-improvements. Review every full diff,
source/ABI, aliasing, byte access order, unsigned behavior and actual clobbers.

Rea does not change the worker sandbox or provide live database access to workers.
It does not certify byte matches, supply a whole-image build or open hardware
gates. Matching coverage remains unknown. No scope expansion, old-task retry,
hardware access, commit or push is implied by a batch-4 run.
