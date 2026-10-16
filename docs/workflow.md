# Agent workflow

## What is ready

The scaffold supplies task validation, an atomic SQLite claim queue, worker
prompts, evidence hashing and review transitions. It does not compile recovered
firmware, compare ARM objects, launch models, or certify matching progress.
The [2026-10-16 bootstrap](bootstrap.md) adds a tested synthetic comparison
prototype and a local Ghidra inventory. It does not certify stock matches or
approve discovered function boundaries. Use Python 3.10+. All commands below
run from the main repository root.

Check configuration and inspect tasks:

```sh
python3 tools/decomp.py check
```

```sh
python3 tools/decomp.py status
```

## First session

Bootstrap setup has now been performed in a single coordinator session, with
no additional agents. Its three reports are submitted for independent review;
do not launch another bootstrap run or a function campaign automatically.
The instructions below describe the queue workflow for later authorized runs.
The corrected inventory review is blocked by saved Ghidra analysis errors;
consult the [review correction](../decomp/results/bootstrap-inventory/notes.md#review-correction)
before accepting the original submitted inventory report or assigning functions.

Start a coordinator with [this prompt](../decomp/prompts/coordinator.md).
Choose the worker models in the agent application or runner. Start with two
inexpensive workers, bounded sessions and an independent reviewer. Exact model
names and pricing are intentionally not hardcoded. No API keys are needed by
the scaffold; the chosen runner handles authentication.

The three initial tasks are inventory/import setup, compiler/ABI research and
a synthetic verifier prototype. They can run independently. These tasks must
produce reviewed foundations before a function campaign; completing their
research alone does not prove that a matching toolchain is available.

After the scaffold is committed, create each worker's isolated worktree from
that commit. This command is an example for the later session:

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
python3 tools/decomp.py claim bootstrap-toolchain --worker worker-a
```

Give that output and the worktree location to the worker's agent session.
Use the same operation with a different task ID for each other worker. Claims
are transactional: competing processes cannot both claim the same task.
Reprint a prompt after a lost terminal session:

```sh
python3 tools/decomp.py packet bootstrap-toolchain
```

Workers produce result.json using [the template](../decomp/templates/result.json)
and notes under their task's allowed directory. The coordinator records a
completed attempt, referencing the worker's actual result file:

```sh
python3 tools/decomp.py submit bootstrap-toolchain --worker worker-a --report .worktrees/worker-a/decomp/results/bootstrap-toolchain/result.json
```

An independent reviewer uses [the review prompt](../decomp/prompts/reviewer.md).
After checking and integrating the bootstrap deliverables, record acceptance:

```sh
python3 tools/decomp.py review bootstrap-toolchain --reviewer reviewer-1 --decision accept --note "Reviewed evidence and integrated the documented toolchain findings"
```

Acceptance records a human/coordinator decision. It is not an automated proof.
Function acceptance is labeled reviewed, never matched. A blocked report cannot
be accepted. Return a submitted attempt for another try using decision requeue.
Release an unfinished claim only after confirming its worker has stopped:

```sh
python3 tools/decomp.py release bootstrap-toolchain --worker worker-a --note "Worker stopped; preserve notes before reassignment"
```

Claims never expire silently. The queue lives in ignored .decomp/queue.sqlite3;
back it up between sessions. Git stores task definitions and reviewed result
notes, not live claims. Changing a previously assigned task definition causes
a deliberate error: reconcile it with the coordinator before continuing.
Identifiers are bookkeeping, not authentication.

## Creating function assignments later

The inventory exporter does not create runnable tasks. Review boundaries,
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

Implement and pin these in the verifier bootstrap, then test them independently:

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

These boundaries are a workflow convention until enforced by the chosen agent
sandbox and independent integration environment. A worktree alone does not
prevent a process accessing another directory or a device.

Run a pilot of 5–10 small leaf functions. Record attempts, elapsed time, actual
model/cost when available and rejection reasons. Escalate ABI, shared types,
interrupts, indirect dispatch and MMIO to stronger review. Apply the worker's
20-minute/8-attempt limit and stop after 3 non-improving attempts.

Track drafts, reviewed functions, exact matches, matched code bytes, recovered
data and whole-image rebuilds separately. The denominator includes undiscovered
regions, padding, tables, vectors and assembly-only code, not just whatever
Ghidra found. Completion requires a reproducible complete stock rebuild with
an exact image hash and an explicit account of every byte; preserved original
code blobs do not count as recovered source. Full equivalence is limited to
the selected input image. Any later firmware change starts a separate phase.
