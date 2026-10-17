# Batch 4 preparation: Rea-assisted intake

2026-10-17. User requested continuation of the Rea integration and next-batch
preparation. This is offline coordinator preparation, not a model-run assignment.
No worker, claim, licence change, hardware access, firmware compilation, commit
or push was performed. Ghidra/LLVM and tool-version checks ran locally.

## Selected and excluded

Three new contiguous Thumb leaves own 94 bytes: fn_00009fe2 (48), fn_00011e38
(16), fn_00015e0c (30). [Addressed review](../../proposals/batch-4-selection.json)
records input/return hypotheses, caller use, widths, unsigned conditions,
memory/aliasing uncertainty and actual register effects. No candidate C was
generated. The byte-store body duplicates reviewed fn_0000e548; this is disclosed,
but its caller-live r3 and separate ownership still require independent review.

fn_00015724 was rejected because it constructs a fixed address and writes words,
even though it has no literal load or call. fn_000178dc branches outside its saved
body. The existing call calibration specimens and terminal-blocked fn_000112b0
were not made new tasks. No verifier extension was attempted to admit them.

## Evidence path

1. Checked pinned Rea archive/bridge, corrected project, inventory, runtime model,
   Ghidra, JDK and sandbox version. Retained source run:
   `.decomp/rea/runs/batch4-intake-01/`. It queried the three selected functions
   plus rejected fn_00015724. Original project hashes remained unchanged.
2. Added [a focused exporter](../../../ghidra/ExportReaIntake.java) and
   [an intake helper](../../../tools/prepare_rea_batch.py). The exporter opens
   only a disposable validated project copy with `-readOnly -noanalysis`, exports
   actual bytes/per-instruction Thumb mode/flow, and repeats admission afterwards.
   It does not change the Rea bridge, compiler or existing analysis pins.
3. Cross-checked all selected instructions against original firmware and an
   independently decoded LLVM wrapper; compared Rea assembly/body ranges against
   the fresh export. Checked unique ownership, entry-only incoming calls and
   internal-only branches against the pinned complete reference export.
4. Froze packets under `.decomp/evidence/rea-batch4-v2/`. Each retains original
   listings, LLVM output, structured instructions, caller context, references,
   metadata and all three Rea responses with their warnings and profile/source
   identity. Full packet hashes are part of the immutable task definitions.
5. Created `.decomp/rea-batch4-v2/lock.json`, SHA-256
   `16c0d91990135f1012122072e5e41514d3100108abcee7c34fcab4c951944703`,
   with unchanged compiler flags, AST policy, linker, comparator, tool/library
   and baseline identities. Local batch admission compares these to the original
   qualified leaf profile. Old locks and packets remain untouched.
6. Integrated the [three definitions](../../proposals/batch-4-leaves.json),
   [batch manifest](../../batches/batch-4-rea-leaves.json) and selected gate/policy.
   All 15 earlier task definitions are byte-content-equivalent as parsed objects.
   The policy changed only its batch pin: quota/window, reserve, concurrency,
   model and attempt/time limits are unchanged. No existing queue state changed.

The first export attempt failed closed because Gson omits null fallthrough
fields. The parser now handles absent nulls while still rejecting out-of-range
fallthroughs. Its failed output remains at `.decomp/rea-batch4-v1/`; it was not
overwritten or admitted. The successful v2 packets are immutable. The intake
tool deliberately refuses existing active IDs and must not be rerun to replace
these assignments.

## Verification

- Batch local preflight reports all three IDs `eligible_after_run_preflight`.
- Main local check validates 18 definitions and their evidence/tool locks.
- Final full regression run, including the three opt-in real Ghidra controls,
  passed **185 tests**. The ordinary suite skips those three controls unless
  explicitly enabled. `git diff --check` and new-file whitespace checks pass.
- [Qualification summary](qualification.json) binds pre-existing synthetic
  negative/repeat controls and ten stock-leaf regressions to the same profile.
  Tool/code/flag/library identities were checked before reuse. This does not
  establish that the new functions match; workers have not tried them.
- Synthetic intake tests reject changed bytes/modes, calls, escaping branches,
  offcut/data entries, constructed fixed-address stores, missing/duplicate/tampered
  Rea observations and changed profile identity. Internal unconditional branches
  and omitted null fallthroughs are handled without altering comparator scope.
- Previous definitions, old comparison pins and all reserve settings were
  independently compared against Git HEAD and preserved. New C files are absent.

Retained evidence identities (SHA-256):

- `.decomp/rea/runs/batch4-intake-01/report.json`:
  `2975403cc83d2a9928fe55564a0478f78df78348d230d12fcd7433f1228c76bd`.
- `.decomp/rea-batch4-v2/work/export.json`:
  `4f6eb55176ffccfb6c69cb89f151e635e2c1606f74c1b734d411be34e34dc9ec`.

## Remaining gates

Preparation needs review/commit before isolated worktrees are created. The user
must assign the three-task run; the coordinator must then check **live** quota,
runner versions, committed state, queue, pause/window and every local pin before
claims. No previous quota reading was reused as permission to launch.

The full image has 128112 bytes. Accounting now declares 288 function bytes,
with 184 reviewed-source bytes, 10 blocked-candidate bytes and 94 newly prepared
bytes. None is a certified matching percentage. No shared-data/interworking/
full-image verifier support was added. Runtime/callee/storage dependencies and
all hardware gates remain unresolved or closed as before.

Use [the current handoff](../../../docs/batch-4.md), not historical batch-3 prompts.
