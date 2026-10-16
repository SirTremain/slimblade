# Coordinator startup prompt

Run an offline decompilation session following AGENTS.md and docs/workflow.md.
The initial repository is scaffolding, not an analyzed firmware project.

First inspect the queue and available local evidence. Record the user's
requested worker count, model choices and spending/time limit. If unspecified,
prepare assignments and request those run parameters before launching paid
jobs. Prefer two inexpensive workers and one coordinator for an initial pilot;
use a stronger reviewer for boundaries, ABI and verifier decisions.

Bootstrap assignments are bootstrap-inventory, bootstrap-toolchain and
bootstrap-verifier. These are independent research/setup assignments; none
asks for firmware function decompilation. Keep one coordinator queue in the
main checkout and distribute separate worktrees and packets to workers.
Do not infer that a submitted bootstrap result establishes a matching build.

Accept bootstrap work only after independent checks. Integrate the approved
memory map, toolchain lock and verifier. Preserve unknowns if the original
compiler cannot be identified; semantic drafts may be useful but are not
matching progress. Require a synthetic positive control and a wrong candidate
that fails the real comparison before scaling workers.

When the user starts function reconstruction, review the exported inventory,
create immutable packets and add real tasks to decomp/functions.json using the
template. Start with a few small leaf functions. Keep volatile MMIO, interrupt,
storage and reset logic for experienced review. Schedule at most one owner per
function; shared tails/types require coordinator decisions.

Run claims and transitions in this main checkout only. Review complete worker
diffs, rebuild independently and recheck prior matches before integration.
Record recovered C, reviewed drafts, exact matches, data coverage, linked image
coverage and unknown regions separately. Queue acceptance is not binary proof.
No hardware access, deployment, automatic commits, pushes or firmware changes.
