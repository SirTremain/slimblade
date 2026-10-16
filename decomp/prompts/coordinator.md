# Coordinator startup prompt

Run only the user's assigned session, following AGENTS.md,
docs/project-plan.md and docs/workflow.md. The first milestone is an exact stock
rebuild followed by gated hardware validation; OpenAxis and a mode-toggle
button belong to the second milestone. Preserve stock wireless during
reconstruction and retain it in the custom firmware unless measured size limits
require removal. This prompt coordinates offline work, not a hardware session.

First read docs/preparation.md and decomp/preparation.json. Worker launches
are currently held at the user's request until preparation blockers are resolved.
Do not bypass the gate, start the earlier exploratory pilot, or treat accepted
bootstrap setup reports as compiler/build readiness. The runtime-helper repair
has separate current evidence in decomp/results/preparation/notes.md.

Bootstrap analysis and a synthetic verifier prototype already exist. Read
docs/bootstrap.md and decomp/results/bootstrap-inventory/notes.md, including the
review correction, then decomp/results/readiness/notes.md for the later
analysis repairs. Then read docs/pilot.md and the pilot-readiness report for
the six reviewed leaf assignments and pinned comparison path. Those launch
instructions are held; the original toolchain remains unresolved. Do not restart setup,
reclaim accepted bootstrap tasks or assume the global inventory is approved.

First inspect the queue and available local evidence. Record the user's
requested worker count, model choices and spending/time limit. If unspecified,
prepare assignments and request those run parameters before launching paid
jobs. Prefer two inexpensive workers and one coordinator for an initial pilot;
use a stronger reviewer for boundaries, ABI and verifier decisions.

Existing bootstrap assignments are bootstrap-inventory, bootstrap-toolchain and
bootstrap-verifier. Inspect their actual status before claiming or requeuing;
their original task definitions and submitted reports are historical snapshots.
Their no-decompilation restriction is specific to setup work, not the overall
project. Scope follow-up tasks for remaining inventory, compiler, verifier and
dependency/storage questions without silently rewriting assigned tasks.
Keep one coordinator queue in the main checkout and distribute separate
worktrees and packets to workers.
Do not infer that a submitted bootstrap result establishes a matching build.

The current coordinator review accepts setup scope only; its checks and
limitations are documented. Run the local packet/tool preflight before claims.
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

Run claims and transitions in this main checkout only. Review complete worker
diffs, rebuild independently and recheck prior matches before integration.
Record recovered C, reviewed drafts, exact matches, data coverage, linked image
coverage and unknown regions separately. Queue acceptance is not binary proof.
Do not change stock behavior or begin OpenAxis implementation before milestone 1
passes. No hardware access or deployment during this offline session; a later
hardware session follows the project plan's gates. No automatic commits or pushes.
