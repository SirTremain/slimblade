# First decompilation pilot

Prepared 2026-10-16: **six leaf functions are ready for bounded offline C
reconstruction and compiler calibration**. No worker has started. No stock C
has been reconstructed. This is not a ready-to-flash build or a general-purpose
matching campaign. The [readiness report](../decomp/results/pilot-readiness/notes.md)
records the checks and the remaining limitations.

## Start here

Review and commit the preparation changes before making worker worktrees;
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
Read AGENTS.md, docs/pilot.md and decomp/prompts/coordinator.md. Prepare to run the six existing pilot tasks in decomp/functions.json; do not restart bootstrap or expand the task list. Run the local preflight and inspect the queue. Before launching any workers, ask me for the worker model, number of concurrent workers and total run budget. Use separate worktrees, the main checkout's queue and the existing immutable packets. Give each worker the complete output of its claim command. Keep the 20-minute, 8-build and 3-non-improving-attempt limits. Independently rebuild and review drafts; exact-range feedback is not match certification. Do not access hardware, change the locked compiler/flags/oracle, commit or push.
```

## Coordinator handoff

The task IDs are `fn_00003b48`, `fn_00003bb4`, `fn_0000e4ee`, `fn_0000e4fc`,
`fn_0000e540`, and `fn_0000e548`. Their combined owned code is 98 bytes, not
a completion percentage. All six are initially unclaimed and have the three
accepted **setup** reports as dependencies. Acceptance is a coordinator review
of setup scope, not full inventory approval or an independent match certificate.
See the [review record](../decomp/results/pilot-readiness/notes.md#bootstrap-review).

After the user assigns a run and budget, create each worktree from the committed
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
directory is the worker worktree. Evidence and tools are read from the main
checkout; results go only into its assigned source/result paths. Do not create
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
build also counts toward the attempt limit. The compiler is a fixed Clang/LLD
23.1.1 candidate, not Kensington's identified historical toolchain. Stop and
report plausible compiler/ABI blockers instead of repeatedly twisting C.

On return, audit the **entire** worker diff, including untracked files; check
allowed paths, readable recovered C, types, side effects and source provenance.
Rebuild independently with the pinned command into a fresh coordinator output
directory. Do not trust worker objects or a worker-written comparison report.
Submit/review using the [workflow](workflow.md); result status is `draft` or
`blocked`, and queue acceptance yields `reviewed`, never `matched`.
Compiler/ABI/source-recovery review is still required even for exact bytes.

## Deliberate limits

The [dependency ledger](dependencies.md) and whole-image gates remain open.
The runtime-helper cluster around `0x1e4f0`, its two callers, inline data and
shared tails remain quarantined; the global inventory checker still fails on
the genuine diagnostic at `0x1e480`. No bookmark or expected byte was changed.
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
by this repository. No proprietary compiler or additional package is required
to start this local pilot. Original compiler provenance and matching coverage
remain unknown; scaling beyond these leaves needs another readiness review.
