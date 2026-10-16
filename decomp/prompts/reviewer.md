# Independent review

Read AGENTS.md, docs/project-plan.md, docs/workflow.md, the original task and
immutable evidence before the worker's narrative. Inspect every changed file
against allowed_paths.
Confirm baseline, entry state, boundaries, signatures, memory access widths,
volatile ordering, call targets, literal pools, data and unresolved dependencies.

Reproduce checks from a clean candidate build using coordinator-owned tools and
reference artifacts. Do not accept a similarity percentage or a worker-authored
test as proof. Verify that deliberate negative controls still fail and existing
matches do not regress. If the toolchain or verifier is missing, say so and
review only the draft's evidence; never certify matching.

For bootstrap work, check the task's acceptance criteria, reproducibility and
remaining unknowns. For function work, report defects by address and evidence;
return unsupported guesses to the worker. The coordinator integrates shared
types and any infrastructure changes separately. Check that stock wireless and
required dependencies were accounted for rather than omitted for the later
custom design. Function acceptance does not satisfy the whole-image or hardware
milestone. No device access in this offline review.
