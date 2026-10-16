# Agent-run preparation — 2026-10-16

User-assigned goal: make the existing six-function pilot executable with
coordinator-owned compilation, enforced worker isolation and a fail-closed
weekly-usage stop. This is preparation, not a stock decompilation run.

Worktree: `.worktrees/swarm-preparation`, based on `137edc3`.
Allowed changes: preparation diagnostics, new worker/supervisor tooling and
tests, readiness/instruction updates. Preserve original firmware, packets,
function definitions, compiler options and comparison semantics. Any necessary
change to pinned build code requires separately versioned reviewed pins and
fresh controls; never silently overwrite a lock.

Do not access hardware, activate licenses, launch firmware workers, commit or
push. Use synthetic worker exercises for preparation. Preserve at least 40%
weekly usage, stop new work at 45% remaining, and fail closed on missing/stale
usage. No purchases or API-billed runs. Initial actual reading: 19% used.

Success requires a repeatable compiler replay and negative controls, tested
worker isolation and bounded orchestration/stop controls, passing offline tests,
and an accurate handoff separating pilot readiness from full-image readiness.
