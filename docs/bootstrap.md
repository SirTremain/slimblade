# Offline bootstrap results

Historical session record, not a new assignment. The
[project plan](project-plan.md) defines current goals; the
[workflow](workflow.md) explains how to continue from these results.

Subsequent status: the [readiness pass](../decomp/results/readiness/notes.md)
resolved three of the four analysis diagnostics on a separate copy, reproduced
the repairs independently, and identified a shared runtime-helper blocker. The
original reports and numbers below remain historical snapshots, not a clean
inventory or a stock-matching pipeline.

Completed 2026-10-16 in one coordinator session from commit
`26175f32029cea2d471020b8e96ec6415c447b18`, using isolated worktree
`.worktrees/bootstrap`. The user requested no additional agents, firmware
reconstruction or device access. None occurred. No paid/model jobs, commits,
pushes, proprietary compiler installs or system package installs were started.
No `yay` command is needed for this completed setup.

| Deliverable | Result and reproduction |
| --- | --- |
| Local tools and official input | Ghidra 12.1.4, Temurin JDK 21.0.12.1+1; official ZIP/EXE/resource/payload hashes verified. [Inventory setup](../decomp/results/bootstrap-inventory/notes.md) |
| Ghidra memory map and inventory | ARM/Thumb `ARM:LE:32:v5t`; 776 discoveries, 35,774 unclassified bytes. Corrected review is blocked by four analysis errors affecting three functions. [Review correction](../decomp/results/bootstrap-inventory/notes.md#review-correction) |
| Compiler investigation | Related SDK map identifies ARM Compiler 5.05 build 41; original SlimBlade compiler/ABI still unknown. [Evidence and calibration proposal](../decomp/results/bootstrap-toolchain/notes.md) |
| Independent comparison prototype | 21 synthetic checks pass with pinned Clang/LLD, reference and verifier; wrong candidates fail. [Commands and trust boundaries](../decomp/results/bootstrap-verifier/notes.md) |
| Coordination and inventory checks | 29 offline tests pass (11 coordination, 18 inventory regression tests); no function tasks created. [Workflow](workflow.md) |

Downloads and original/generated binary evidence stay under ignored `.decomp/`.
Ghidra projects stay under ignored `ghidra/projects/`, because the pinned
release rejects hidden path components in project locations. Source scripts,
notes and provenance metadata are under the three `decomp/results/bootstrap-*`
directories. The scripts require no Python third-party packages.

The three queue reports are submitted, not independently accepted. This session
used independent tools and fresh builds for validation, but did not impersonate
a second reviewer. The synthetic verifier is not the missing stock matching
pipeline: matching coverage remains **unknown**, and no recovered function is
claimed. Whole-image stock reconstruction still requires the compiler/ABI,
complete byte ownership, reviewed boundaries, data recovery and exact container
rebuild. Discovery counts are not a completion percentage.

The pre-commit review correction preserves those submitted report snapshots and
the original evidence. Fresh read-only exports and a new validation report
supersede the initial clean structural verdict. The analysis errors have been
exposed, not repaired; the Ghidra database, function boundaries and firmware
bytes were not changed. See the inventory notes before accepting the old report.

The historical [marker reachability gate](marker-reachability-gate.md) is
unchanged. The replacement device's hardware revision and installed firmware
are still unknown.
