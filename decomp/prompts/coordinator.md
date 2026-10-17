# Coordinator startup prompt

Run only the user's assigned session. Read AGENTS.md, docs/project-plan.md,
docs/workflow.md, docs/preparation.md, docs/broader-workflow.md, docs/batch-4.md,
docs/rea.md and docs/swarm.md.
Current offline scope is **batch 4 only**: fn_00009fe2, fn_00011e38 and fn_00015e0c.
Batches 1–3 are terminal: eleven reviewed drafts and fn_000112b0 blocked. Do not release,
reclaim or requeue those tasks. The two earlier call-wrapper calibration
specimens are not worker tasks. The selected batch, dependency ledger and
qualification evidence are pinned in decomp/batches/batch-4-rea-leaves.json.

The goal remains a complete exact stock reconstruction followed by separately
gated hardware validation. OpenAxis and the mode-toggle button belong to a later
milestone. Preserve all stock behavior, including wireless, during reconstruction.
No hardware access, loader entry, HID/vendor reports, resets or flashing during
this run. Preparation alone is not an instruction to start a model job.

Before claims, check the committed preparation, main queue, local packet/tool
pins, runner versions, live weekly quota, policy window and PAUSED.json.
The three new leaf definitions use a separate task lock and the unchanged ARMCC5
leaf profile. All earlier definitions, packets and compiler locks must remain
unchanged. No candidate C has been generated for batch 4; retained Rea pseudocode
is an unverified hypothesis, not an accepted source draft. Exact-range feedback is not
proof of the original compiler, original declaration or whole-image equivalence.
The global inventory remains unapproved. Do not reopen historical licence or
runtime-helper investigations; their scoped preparation evidence is recorded.

Use tools/swarm_worker.py, not inherited-permission subagents. At most two
gpt-6-luna workers may run concurrently; gpt-6.1-sol is for a bounded escalation.
Use ChatGPT sign-in, not API billing. Stop at 45% weekly usage remaining to
preserve at least 40% for work; monitor coordinator usage too. Fail closed on
missing/stale quota or a changed window. Never clear a pause or renew a window
without an explicit user resume/new assignment. No purchases or credit top-ups.

Create isolated worktrees from the preparation commit. Claim in the main queue
only, immediately before launch. Each worker owns only its assigned C file and
result directory; packets and selected instructions are read-only. Never expose
the compiler, private Wine prefix, licence files, calibration sources or full
artifact tree. Workers must not spawn agents, edit shared types, change pins,
modify Ghidra, or operate the queue. The coordinator owns integration.

Compile only through tools/swarm_build.py, which serializes builds and enforces
the queue identity, pins, live quota and persistent attempt ledger. Use normal
command approval for coordinator builds outside the incompatible outer Codex
sandbox; retain the compiler's dedicated sandbox. Never escalate workers or
disable global sandboxing. Use the same frozen flags, baseline and boundaries.

Each task has 20 minutes from claim across all worker/build turns, at most eight
attempts, and stops after three without improvement. Do not release/reclaim to
reset limits. A compiler-busy scheduling collision does not consume an attempt.
An independent unchanged-source rebuild after the worker deadline has its own
ten-minute bound, not another source-editing turn. Respect existing ledgers.

Audit every complete worktree diff, not just the C file. Independently review
source provenance, ABI, widths, signedness, aliasing, memory access order,
register clobbers, stack effects and caller assumptions against addressed evidence.
fn_00011e38 must preserve byte store order and caller-live r3; fn_00009fe2 and
fn_00015e0c require full-width unsigned conditions and shifts, not assumptions
that every caller supplies a byte. Preserve Rea caveats and compare against
original instructions. No calls or absolute globals in these leaves. No embedded code bytes, inline assembly,
intrinsics, stubs, post-link patches or omitted behavior masquerading as C.
Signature corrections require coordinator review, not silently changing a lock.

For an exact candidate, run the fresh unchanged-source --review rebuild before
submission. Review source/ABI separately from byte equality. Once workers stop,
submit and record acceptance as reviewed, never matched. Preserve evidence-backed
blocked attempts and their limits. Integrate only allowed source/reports; no
automatic commits, pushes, task additions or scope expansion. Continue only
until the three assigned tasks are reviewed/blocked or the reserve guard stops.
Use the terminal block review decision for an evidence-backed blocked report;
do not release/reclaim to reset limits or automatically resume it.
Report draft/reviewed status separately from certified matches and whole-image
progress; matching coverage remains unknown.
