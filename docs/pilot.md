# First decompilation pilot

Updated 2026-10-16: **six leaf assignments are prepared for a user-budgeted run**.
[Preparation evidence](preparation.md) records ARMCC5 calibration and comparison
checks. The new ARMCC lock is separately versioned; the old Clang lock and all
original evidence packets remain intact. No worker has started.

## Start here

Review and commit preparation changes before making worker worktrees;
new worktrees start from a commit, not the coordinator's uncommitted files.
No commit or push was performed during preparation. Keep the ignored local
`.decomp` artifacts: the published source alone does not contain the firmware,
packets or compiler lock. Run this preflight from the main checkout:

```sh
python3 tools/decomp.py check --local
```

```sh
python3 tools/decomp.py status
```

Use a coordinator session in the main checkout. Copy **only the contents of
the following text block** into that session. The block is the entire prompt:

```text
Read AGENTS.md, docs/preparation.md, docs/pilot.md and decomp/prompts/coordinator.md. Check the local evidence/tool locks and queue. Prepare the existing six ARMCC5 leaf assignments from committed changes. Before launching workers, ask me for model choices, concurrency and a total run budget if I have not supplied them. Keep each worker in an isolated worktree with only its assigned paths writable. Run licensed compiler requests serially as coordinator; do not give workers the private Wine prefix or license files. Independently rebuild and review every submitted draft. Do not add tasks, change pins, claim certified coverage, access hardware, commit or push.
```

## Coordinator handoff

The task IDs are `fn_00003b48`, `fn_00003bb4`, `fn_0000e4ee`, `fn_0000e4fc`,
`fn_0000e540`, and `fn_0000e548`. Their combined owned code is 98 bytes, not
a completion percentage. All six are initially unclaimed and have the three
accepted **setup** reports as dependencies. Acceptance is a coordinator review
of setup scope, not full inventory approval or an independent match certificate.
See the [review record](../decomp/results/pilot-readiness/notes.md#bootstrap-review).

After local preflight passes and the user assigns a run and budget,
create each worktree from the committed
preparation. Example for the first worker, from the main checkout:

```sh
git worktree add .worktrees/worker-a -b decomp/worker-a HEAD
```

Claim only when the worker is ready to start; the entire command output is its
prompt, including a concrete pinned comparison command:

```sh
python3 tools/decomp.py claim fn_00003b48 --worker worker-a
```

Give that prompt and the absolute worktree location to the worker. Its working
directory is the worker worktree. Expose its assigned evidence packet read-only,
not the main checkout's private compiler/license directories. Results go only
into its assigned source/result paths. Do not create
a queue in each worktree. A second worker needs a different worktree, branch,
worker ID and task. Reprint a claimed prompt if needed:

```sh
python3 tools/decomp.py packet fn_00003b48
```

Workers do not need to open Ghidra: their packets already include addressed
bytes, Ghidra and LLVM listings, per-instruction Thumb state, flow information,
callers and unresolved type questions. A Ghidra database is single-writer
coordinator state, not a shared worker workspace. Pseudocode is optional and
has deliberately not been generated in this preparation.

The packet's comparison command uses a fresh numbered output directory per
attempt. Exit status 0 means exact bytes for the owned range, 2 means byte/size
mismatch, and 1 means source/build/trust-input rejection. Compare lengths and
byte differences; do not optimize a percentage or change boundaries. A rejected
build also counts toward the attempt limit. The compiler is ARMCC 5.06u7 b960
under Wine; LLD 23.1.1 performs strict isolated-leaf layout. This profile matched
all six fixed calibration examples; it is not proof of the historical version
or a complete firmware linker. Stop and report evidence-backed ABI/boundary
questions instead of repeatedly twisting C to match a guessed declaration.

The coordinator executes the printed build command from the worker worktree
and returns the redacted result directory. Compiler requests are serialized;
the prefix lock rejects overlaps. A busy-lock scheduling retry is not a source
attempt. Keep the genuine host/prefix used for licensing; no GUI or Windows
desktop is needed. Do not run license diagnostics concurrently with builds.
See [the build review](../decomp/results/preparation/armcc-calibration.md).

On return, audit the **entire** worker diff, including untracked files; check
allowed paths, readable recovered C, types, side effects and source provenance.
Rebuild independently with the pinned command into a fresh coordinator output
directory. Do not trust worker objects or a worker-written comparison report.
Submit/review using the [workflow](workflow.md); result status is `draft` or
`blocked`, and queue acceptance yields `reviewed`, never `matched`.
Compiler/ABI/source-recovery review is still required even for exact bytes.

## Deliberate limits

The [dependency ledger](dependencies.md) and whole-image gates remain open.
The subsequent runtime-helper repair resolves the saved diagnostic and models
both callers' real exits, supported by original-byte execution tests and a
repeatable bounded analysis delta. No firmware byte changed. This is analysis
preparation, not recovered C or proof of every discovered function boundary.
The six individually reviewed leaves have no calls, absolute-address accesses,
literal pools or shared tails. Their own boundaries and bytes were checked;
this does not approve the rest of the 776 discoveries.

The current comparator intentionally rejects calls, external symbols, absolute
addresses, extra functions, global/static data, assembly and compiler intrinsics.
It includes compiler-generated literal pools in text, compares exact size and
all executable load bytes at the original address, and rejects extra allocated
sections. Calls, relocatable dependencies, shared data, ARM functions and full
image packaging require a separately reviewed extension before assignment.
The earlier synthetic verifier still tests call relocations and data/BSS; those
tests do not imply these features are supported by this leaf comparator.

Same-UID processes can bypass filesystem conventions. Worktrees and read-only
files are not a security sandbox. Configure the runner to deny device access
and writes outside worker-owned paths; the coordinator retains the trusted
reference and independently checks all output. No provider or model is launched
by this repository. The six-task preparation gate does not start a worker run.
Original compiler provenance and matching coverage remain unknown; scaling
beyond these leaves also needs a separate readiness review.
