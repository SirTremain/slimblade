# Coordinator startup prompt

Run only the user's assigned session, following AGENTS.md,
docs/project-plan.md and docs/workflow.md. The first milestone is an exact stock
rebuild followed by gated hardware validation; OpenAxis and a mode-toggle
button belong to the second milestone. Preserve stock wireless during
reconstruction and retain it in the custom firmware unless measured size limits
require removal. This prompt coordinates offline work, not a hardware session.

First read docs/preparation.md and decomp/preparation.json. The explicit six-leaf
scope now has ARMCC5 calibration and pinned build/comparison checks. Validate
local pins before claims; do not infer broader readiness from accepted setup
reports or the old exploratory pilot. The runtime-helper repair and compiler
qualification have current evidence in decomp/results/preparation/notes.md and
decomp/results/preparation/armcc-calibration.md.

Bootstrap analysis and a synthetic verifier prototype already exist. Read
docs/bootstrap.md and decomp/results/bootstrap-inventory/notes.md, including the
review correction, then decomp/results/readiness/notes.md for the later
analysis repairs. Then read docs/pilot.md and the pilot-readiness report for
the six reviewed leaf assignments and the new ARMCC5 comparison path. The exact
historical toolchain is still unidentified, not a license/setup blocker for
this calibrated scope. Do not restart setup,
reclaim accepted bootstrap tasks or assume the global inventory is approved.

Read docs/swarm.md and decomp/swarm-policy.json. Use the tested isolated CLI
runner, not ordinary subagents inheriting coordinator permissions. The user's
current budget retains 40% weekly quota, stops at 45% remaining, and permits at
most two Luna workers with bounded Sol escalation. Confirm a firmware run was
assigned; preparation itself is not a launch request. Check the dated quota
window, live account reading and pause latch. Never silently renew a window,
clear a stop, purchase credits or use API billing. Poll coordinator usage too.
Keep the Goal active only within those limits and the six-task scope.

Existing bootstrap assignments are bootstrap-inventory, bootstrap-toolchain and
bootstrap-verifier. Inspect their actual status before claiming or requeuing;
their original task definitions and submitted reports are historical snapshots.
Their no-decompilation restriction is specific to setup work, not the overall
project. Scope follow-up tasks for remaining inventory, compiler, verifier and
dependency/storage questions without silently rewriting assigned tasks.
Keep one coordinator queue in the main checkout and distribute separate
worktrees and packets to workers.
Do not infer that a submitted bootstrap result establishes a matching build.

Bootstrap acceptance covers setup only; the later preparation review is scoped
to these six leaves. Run the local packet/tool preflight before claims.
Preserve unknowns if the original compiler cannot be identified; semantic
drafts may be useful but are not matching progress. The supplied range
comparator uses a fixed candidate toolchain, not a proven historical one.
Reproduce controls and require another readiness review before expanding beyond
the six leaves. Do not silently replace the toolchain lock to improve scores.

For the first assigned reconstruction run, use the six existing tasks and
immutable packets in decomp/functions.json. Do not add more tasks automatically.
Later expansion requires reviewed boundaries, dependencies and an extended
verifier before using the template. Keep volatile MMIO, interrupt,
storage and reset logic for experienced review. Schedule at most one owner per
function; shared tails/types require coordinator decisions.

Run claims and transitions in this main checkout only. Launch bounded turns
through tools/swarm_worker.py and build through tools/swarm_build.py. The latter
preserves the pinned comparison command and serializes the compiler. Request
normal command approval to run coordinator builds outside the incompatible
outer Codex sandbox; leave the dedicated compiler sandbox enabled. Never expose
private licence files or the Wine prefix to workers. Preserve ledgers and do not
release/reclaim tasks to reset budgets. A compiler-busy scheduling retry does
not consume a source attempt. Independently rebuild unchanged exact source
with --review before queue submission; review source and ABI separately.
Review complete worker
diffs, rebuild independently and recheck prior matches before integration.
Record recovered C, reviewed drafts, exact matches, data coverage, linked image
coverage and unknown regions separately. Queue acceptance is not binary proof.
Do not change stock behavior or begin OpenAxis implementation before milestone 1
passes. No hardware access or deployment during this offline session; a later
hardware session follows the project plan's gates. No automatic commits or pushes.
