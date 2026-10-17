# Agent workflow

## Scope and document roles

The [project plan](project-plan.md) owns the current goals and milestone gates:
exact stock reconstruction and hardware validation first, OpenAxis and a
mode toggle second. This document covers offline coordination within that plan.
Hardware testing is a later, explicitly requested session, not an action for a
decompilation worker. Preserve all wireless behavior during stock reconstruction;
any size-driven wireless removal belongs only to the later custom branch.

[AGENTS.md](../AGENTS.md) supplies working rules. Bootstrap reports and
[legacy notes](legacy.md) retain historical evidence; they do not override the
plan. The original bootstrap task definitions remain unchanged because the
queue locks assigned definitions. Their setup-only restrictions are task-local.
Use separately scoped follow-up tasks after review instead of silently changing
submitted assignments or treating old startup prompts as a new work order.

## What is ready

The [first six-task run](../decomp/results/pilot-run-20261016/notes.md) is complete:
all six drafts are reviewed and independently rebuilt. Do not reclaim them.
The [second run](../decomp/results/batch2-run-20261017/notes.md) is also complete;
do not reclaim its four tasks. Batch 3 is also terminal: fn_0000be60 reviewed and
fn_000112b0 blocked. [Batch 4](batch-4.md) selects three fresh Rea-assisted leaves.
The global inventory and calibration specimens remain outside the active gate.

**Three batch-4 leaf assignments are prepared** under the explicit scope in
[preparation.json](../decomp/preparation.json). The compiler/helper preparation
blockers have supporting closure evidence in [preparation.md](preparation.md).
Missing/malformed gates, changed pins or out-of-scope task IDs fail closed.
Passing configuration checks is not a full-image verdict or a worker launch;
the user must still assign models, concurrency and a total run budget.

The scaffold supplies task validation, an atomic SQLite claim queue, worker
prompts, evidence hashing and review transitions. The [first pilot](pilot.md)
adds six reviewed leaf packets and a pinned source-build/exact-stock-range
comparison command. Queue commands do not launch models, certify progress or
build the complete firmware. ARMCC5 is calibrated for this scope, not identified
as the exact historical compiler. The global inventory remains unapproved.
Use Python 3.10+. Queue commands run from the main repository root; the
coordinator runs guarded ARMCC builds using [the runner](swarm.md).

Check configuration and inspect tasks:

```sh
python3 tools/decomp.py check --local
```

```sh
python3 tools/decomp.py status
```

## Continuing from bootstrap

Bootstrap setup is complete. Its three reports have coordinator acceptance
for their original setup scope, with the [pilot-readiness addendum](../decomp/results/pilot-readiness/notes.md#bootstrap-review).
Do not restart bootstrap or launch workers automatically. The subsequent
[preparation work](../decomp/results/preparation/notes.md) repairs the runtime
helper model and inline-data classification; its corrected inventory passes
structural checks. The subsequent ARMCC5 calibration and pinned comparison
checks support the six-leaf run. No compiler/license setup remains for that
scope; full-image linking and broader function support are later work.

Start with [the batch-4 handoff](batch-4.md#next-run), which references
the [coordinator instructions](../decomp/prompts/coordinator.md).
The user assigns a run before any firmware launch. The existing budget policy
uses at most two Luna workers, with a 45%-remaining stop to preserve a 40% weekly
work reserve. It is not unlimited authorization or an automatic weekly renewal.
Use [the bounded runner](swarm.md), ChatGPT sign-in and independent review;
no API keys or API-billed runs are part of this setup.

The three original tasks covered inventory/import setup, compiler/ABI research
and a synthetic verifier prototype. Their acceptance does not prove a matching
toolchain or full inventory is available. Resolve the remaining
[dependency/storage questions](dependencies.md) and extend/review the verifier
before assigning unsupported call/data shapes or claiming full-image verification.
Batch 3 uses a separately pinned direct-call profile and explicit callee contracts.

Create each worker's isolated worktree from a commit containing the current
instructions and tools. The commands below are queue-operation examples, not
instructions to reclaim accepted bootstrap tasks. Substitute the
actual pending task, worker and report for the assigned run.

```sh
git worktree add .worktrees/worker-a -b decomp/worker-a HEAD
```

Use distinct worktrees and branches for other workers. Workers must start from
a commit containing the scaffold; worktrees do not inherit uncommitted files.
Only the coordinator runs the queue commands in the main checkout. This avoids
a separate queue per worktree. For orchestration from elsewhere, specify the
same absolute main checkout with --root and the same --state SQLite path.

Claim an assignment; stdout is the complete worker prompt:

```sh
python3 tools/decomp.py claim fn_00009fe2 --worker worker-a
```

Launch through [swarm_worker.py](../tools/swarm_worker.py), as described in
[the guarded procedure](swarm.md). It supplies the prompt and mounts only the
task's inputs/outputs; do not paste it into an unrestricted worker session.
Use the same operation with a different task ID for each other worker. Claims
are transactional: competing processes cannot both claim the same task.
Reprint a prompt after a lost terminal session:

```sh
python3 tools/decomp.py packet fn_00009fe2
```

Workers produce result.json using [the template](../decomp/templates/result.json)
and notes under their task's allowed directory. The coordinator records a
completed attempt, referencing the worker's actual result file:

```sh
python3 tools/decomp.py submit fn_00009fe2 --worker worker-a --report .worktrees/worker-a/decomp/results/fn_00009fe2/result.json
```

An independent reviewer uses [the review prompt](../decomp/prompts/reviewer.md).
After auditing the complete diff and independently rebuilding/reviewing the
function draft, record review acceptance:

```sh
python3 tools/decomp.py review fn_00009fe2 --reviewer reviewer-1 --decision accept --note "Reviewed source and independently rebuilt; not match certification"
```

Acceptance records a human/coordinator decision. It is not an automated proof.
Function acceptance is labeled reviewed, never matched. A blocked report cannot
be accepted. Use review decision `block` for an evidence-backed blocked report;
it remains terminal and cannot be reclaimed to reset limits. A deliberate
requeue/release requires a separately reviewed retry budget, not an automatic
loop. Release an unfinished claim only after confirming its worker has stopped:

```sh
python3 tools/decomp.py release fn_00009fe2 --worker worker-a --note "Worker stopped; preserve notes before reassignment"
```

Claims never expire silently. The queue lives in ignored .decomp/queue.sqlite3;
back it up between sessions. Git stores task definitions and reviewed result
notes, not live claims. Changing a previously assigned task definition causes
a deliberate error: reconcile it with the coordinator before continuing.
Identifiers are bookkeeping, not authentication.

## Creating function assignments later

Optional [Rea-backed analysis](rea.md) supplies retained function dossiers from
the corrected project for coordinator intake. It does not reopen completed or
blocked tasks, change frozen evidence, or launch workers. Preserve its caveats
alongside original bytes when preparing a new packet; existing admission and
compiler/review gates still apply.

The inventory exporter does not create runnable tasks. The three batch-4 tasks
are already prepared and batches 1–3 are terminal; do not regenerate or reclaim
them on startup. For later work,
review boundaries,
instruction state and data ownership, then add task objects to the functions
array in [functions.json](../decomp/functions.json) using
[the template](../decomp/templates/function.json). The initial schema assumes
flat container offsets; RAM-resident code or overlapping/shared tails require
an explicit mapping/ownership extension, not invented boundaries.

Keep one immutable directory per function under .decomp/evidence/<id>:

| File | Required content |
| --- | --- |
| metadata.json | baseline_sha256, entry, mode, ranges (same fields as the task), tool versions, export settings |
| listing.txt | Addressed original instruction bytes, disassembly and associated literals/data |
| context.md | Callers/callees, referenced globals, types, MMIO and side effects; unknowns marked |
| pseudocode.c.txt | Optional Ghidra draft, clearly unverified |
| Other files | Relevant data excerpts, known prototypes and prior failed attempts |

Record the packet's deterministic hash in evidence_sha256:

```sh
python3 tools/decomp.py hash-packet .decomp/evidence/fn_00000000
```

That ID is a placeholder: substitute a reviewed real function. Hashing covers
sorted relative filenames and every file's SHA-256, rejects symlinks, and
changes if any file is added, removed, renamed or edited. Claims fail if the
packet or baseline metadata no longer agrees. Transfer identical packets to
workers outside tracked source; a coordinator retains the originals.

Workers own only their function C file and result directory. Shared headers,
symbols, boundary changes, toolchain flags and Ghidra edits are proposals for
the coordinator. One owner edits the Ghidra database; workers consume exported
packets or independent project copies.

## Verification before scaling

The current leaf comparator implements pinned real-range feedback for its
restricted scope. The [direct-call workflow](broader-workflow.md) adds qualified
call controls and guarded batch dispatch; the older synthetic prototype also
tests data. None is full stock proof. For broader work, require all of the following
in the extended verifier and test independently:

1. Hash-lock original input, tools, compiler version, flags, ABI, linker settings
   and verifier revision. Keep the oracle/reference files outside worker writes.
2. Compile candidate C and link at original addresses with fixed external
   symbols. Compare function bytes, literal pools, data and call targets.
   Object diffs are useful feedback; do not simply ignore relocation bytes.
3. Make wrong constants, signedness, missing stores, changed calls, changed
   data and deliberately damaged targets fail. Reject inline assembly,
   embedded target bytes and post-link instruction patching as C recovery.
4. Rebuild independently of worker outputs and rerun every existing match
   before merging. Audit the full diff for changes outside allowed paths.

The [bounded runner](swarm.md) enforces the worker mount/permission boundary;
a worktree alone does not prevent another-directory or device access. Use
coordinator-owned independent rebuilds and source review as separate checks.

With local pins verified and a user-assigned budget, run only the active batch.
The first six-leaf pilot is complete. Serialize compiler requests through the
coordinator; workers never receive the private Wine prefix or license files.
Record attempts, elapsed time, actual
model/cost when available and rejection reasons. Escalate ABI, shared types,
interrupts, indirect dispatch and MMIO to stronger review. Apply the worker's
20-minute/8-attempt limit and stop after 3 non-improving attempts.

Track drafts, reviewed functions, exact matches, matched code bytes, recovered
data and whole-image rebuilds separately. The denominator includes undiscovered
regions, padding, tables, vectors and assembly-only code, not just whatever
Ghidra found. Completion requires a reproducible complete stock rebuild with
an exact image hash and an explicit account of every byte; preserved original
code blobs do not count as recovered source. Full equivalence is limited to
the selected input image. This completes the offline reconstruction gate, not
the entire first milestone: dependency/recovery review, gated flashing and
stock hardware validation still follow under the [project plan](project-plan.md).
Do not begin the OpenAxis custom phase until that milestone passes.
