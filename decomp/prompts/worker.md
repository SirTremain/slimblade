# Worker assignment

Read root AGENTS.md, docs/project-plan.md and docs/workflow.md. This worker
prompt covers offline stock reconstruction, not feature changes or flashing.
Preserve all stock behavior, including wireless; the later custom phase does
not justify omitting code from the stock build. Work in the assigned isolated
worktree. The coordinator supplies the task below and, for function tasks, a
hash-locked local evidence directory. Do not choose extra tasks or launch more
agents. Do not access hardware or run a retired binary from ignored directories.

Edit only allowed_paths in the task. For bootstrap tasks, put proposed shared
files under the assigned result directory for the coordinator to integrate.
For function tasks, treat listing bytes as primary evidence; check instruction
state, boundaries, callers, callees, literal pools, data, side effects and types.
Ghidra pseudocode is a fallible draft. Do not turn assumptions into facts.

Use the pinned compile/diff command only if the coordinator supplies a working
verifier. If it is absent, produce an evidence-backed draft or a blocker, and
explicitly report that no match was verified. Never alter the baseline, shared
types, toolchain, build flags, comparison rules, reference assembly or bytes.
The claim output includes the pinned comparator contract; read
docs/broader-workflow.md for scope and callee contracts. For ARMCC builds, send the command/source path to the
coordinator and await the redacted outputs. Do not access its private Wine
prefix or license files. The calibrated profile reports exact-range bytes or a mismatch, never certified
matching coverage. Original compiler provenance and source declaration details
remain hypotheses. Do not use inline assembly/intrinsics or expand your body
to absorb padding. The leaf comparator forbids calls; the separate call profile
permits only explicitly pinned ordinary direct Thumb calls and declarations.
Neither supports absolute data addresses/globals or arbitrary interworking.
Fixed external callees are dependencies, not reconstructed code. Request a
coordinator decision if evidence needs unsupported behavior.

Default function budget: 20 minutes, 8 compile/diff attempts maximum; stop after
3 attempts with no improvement. A smaller assigned budget takes precedence.
Record cost/token usage if available; do not invent it. Escalate boundary,
ABI, MMIO, interrupt or shared-type uncertainties rather than guessing.

Write decomp/results/<task-id>/result.json using decomp/templates/result.json,
and concise notes.md with addresses and evidence. Finish with status draft or
blocked. Hand the coordinator the branch/worktree, changed paths and report
path. Do not mark yourself matched, merge, commit or push without instruction.
