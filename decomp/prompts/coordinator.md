# Coordinator startup prompt

Run only the user's assigned session, following AGENTS.md,
docs/project-plan.md and docs/workflow.md. The first milestone is an exact stock
rebuild followed by gated hardware validation; OpenAxis and a mode-toggle
button belong to the second milestone. Preserve stock wireless during
reconstruction and retain it in the custom firmware unless measured size limits
require removal. This prompt coordinates offline work, not a hardware session.

Bootstrap analysis and a synthetic verifier prototype already exist. Read
docs/bootstrap.md and decomp/results/bootstrap-inventory/notes.md, including the
review correction, then decomp/results/readiness/notes.md for the later
analysis repairs and remaining runtime-helper/compiler/verifier blockers.
Do not restart setup or assume the inventory is approved.

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

Accept bootstrap work only after independent checks. Integrate the approved
memory map, toolchain lock and verifier. Preserve unknowns if the original
compiler cannot be identified; semantic drafts may be useful but are not
matching progress. Require a synthetic positive control and a wrong candidate
that fails the real comparison before scaling workers.

For an assigned reconstruction run, review the exported inventory,
create immutable packets and add real tasks to decomp/functions.json using the
template. Start with a few small leaf functions. Keep volatile MMIO, interrupt,
storage and reset logic for experienced review. Schedule at most one owner per
function; shared tails/types require coordinator decisions.

Run claims and transitions in this main checkout only. Review complete worker
diffs, rebuild independently and recheck prior matches before integration.
Record recovered C, reviewed drafts, exact matches, data coverage, linked image
coverage and unknown regions separately. Queue acceptance is not binary proof.
Do not change stock behavior or begin OpenAxis implementation before milestone 1
passes. No hardware access or deployment during this offline session; a later
hardware session follows the project plan's gates. No automatic commits or pushes.
