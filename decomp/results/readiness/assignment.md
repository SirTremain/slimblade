# Offline readiness pass

Assigned by the user on 2026-10-16: investigate and correct the four known
Ghidra analysis errors, then assess compiler/verifier readiness for a small
stock-reconstruction pilot. No additional agents, device access or firmware
behavior changes. No stock C reconstruction is required in this pass.

Work in `.worktrees/readiness`, based on commit
`21abcd4e01540cf08ea4a03870bb4f1e1a99fef8`. Allowed source paths:
`decomp/results/readiness/`. The coordinator may integrate these files and
update current-status links in the main checkout after checking the diff.
Keep generated/proprietary evidence under the main ignored `.decomp/` tree.

Use a separately named Ghidra project copied from the bootstrap project.
Preserve the baseline project and frozen evidence. Analysis changes require
original-byte assertions, addressed control-flow evidence, an independent
disassembler crosscheck, before/after exports and unchanged container bytes.
Do not clear a diagnostic merely to make the review pass. Record unresolved
control-flow modeling and ownership as blockers. Do not approve queue tasks or
certify matches during this pass.

Stop compiler investigation at any account, license, purchase or system-install
boundary; report the exact missing prerequisite. Recheck the existing synthetic
verifier without presenting it as a real firmware verifier.
