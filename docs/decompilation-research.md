# Research: decompilation and agents

Checked 2026-10-16. Sources below are tool/project maintainers' documentation,
not claims that any of these projects supports the BK3635 out of the box.
Downloaded documentation identities are in [research-sources.json](research-sources.json).

## What the tools actually do

[decomp.dev](https://decomp.dev/) tracks decompilation progress. Its current
sunsetting announcement says the main index and new-project registration are
disabled; existing project pages and history continue. Its navigation links to
[Decompedia](https://decomp.wiki/), the community wiki. Search-indexed GitHub
README content was stale and direct repository/wiki requests returned 404.
The current site was retrieved directly and its HTML identity recorded below.

[Decompedia's maintained source](https://github.com/decompals/decompedia/blob/main/home.md)
explains matching decompilation and links platform guides, decomp.me and the
shared Ghidra service at ghidra.decomp.dev. These are useful community resources;
no BK3635 recipe or universal multi-agent procedure was found. A community
Ghidra server is an alternative for shared projects, not a requirement here.

[Ghidra](https://github.com/NationalSecurityAgency/ghidra) combines disassembly,
decompilation, reference graphs, types and scripting. Its C-like output is an
analysis aid. Reconstructing original source names, types, file boundaries and
a reproducible build requires further work. The
[headless interface](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md)
supports repeatable import and export; project locking favors one maintained
database plus worker snapshots/packets. It does not supply a matching compiler.

For learning Ghidra, start with its
[official beginner course](https://ghidra.re/ghidra_docs/GhidraClass/Beginner/Introduction_to_Ghidra_Student_Guide.html),
which covers raw-binary import, language/compiler selection, analysis, types,
graphs and exports. The proposed GUI-first setup followed by scripted exports
uses documented capabilities. The queue, packet format and agent roles in this
repository are project-specific choices, not Ghidra or decomp.dev requirements.

[objdiff](https://github.com/encounter/objdiff) compares relocatable object files,
including functions and data, supports ARM, and produces decomp.dev-compatible
progress reports. It is suitable feedback after a target-object and candidate
build pipeline exists. The SlimBlade resource is a flat firmware container,
so a project-specific mapping, symbol and reference-object step is needed first.
A displayed similarity score is not a whole-firmware correctness proof.

[pret/pokeemerald](https://github.com/pret/pokeemerald) is a concrete ARM game
example with source, data, assembly, linker scripts, symbols and a documented
expected ROM checksum. Its build instructions use a specific toolchain.
The transferable lesson is the independently reproducible final binary.
Its compiler and GBA memory layout are not evidence about the SlimBlade.

## Public agent organization

| Project | Documented approach | Adaptation here |
| --- | --- | --- |
| [decomp.wtf](https://github.com/i12bp8/decomp.wtf) | Per-function claims and evidence; compile/link/diff feedback; coordinator owns shared work | Atomic claims, immutable packets and worker-owned C files |
| [djsaunde/decomp agent guide](https://github.com/djsaunde/decomp/blob/main/CLAUDE.md) | Parallel Git worktrees, preflight checks, exact-result records and gated integration | Separate worker worktrees, recorded attempts and independent review |
| [objdiff](https://github.com/encounter/objdiff) | Function/data comparison and progress reports | Proposed verifier feedback; matching progress stays unknown until implemented |

The decomp.wtf README describes restricted worker writes and regression checks,
and distinguishes matched functions from fully linked files. It also documents
small-function routing and bounded attempts. Its repository was archived on
2026-10-15 and its README says development is discontinued. Treat it as a design
reference, not a maintained dependency or a verified solution for this MCU.

The N64 agent guide explicitly rejects instruction patching used to manufacture
matches. Its merge workflow requires exact results and per-function records.
That is useful evidence for keeping the reference, compiler configuration and
verifier outside each worker's assignment.

These are examples of agent workflows; they are not a claim that game
decompilation projects generally use or welcome AI contributions. This setup
does not submit anything to those projects.

## Recommendation and limits

This section records the original scaffold rationale. The
[project plan](project-plan.md) defines the current milestone order and priorities;
the bootstrap setup below has already been performed and is under review.

Use a small provider-independent coordinator, exported Ghidra evidence and
isolated workers. Start with inventory, compiler research and a verifier
prototype, then calibrate inexpensive workers on a few small leaf functions.
Use stronger review for shared types, ABI, interrupts and MMIO. Measure actual
cost per accepted result before expanding concurrency.

This recommendation is an inference from the workflows above and the
[recorded stock evidence](stock-baseline.md). A large model swarm should not
precede an objective acceptance test. More workers cannot resolve an unknown
compiler or a wrong memory map merely by producing more plausible C.

The first target is a reproducible stock rebuild, dependency/recovery review
and gated hardware validation, followed by the separate OpenAxis
modification phase. Ghidra output alone is not that rebuild. Even complete
matching only covers the chosen image; calibration, undocumented hardware
behavior and later modifications remain separate concerns. Offline file
analysis avoids device writes. Flashing modified firmware can still brick it.
