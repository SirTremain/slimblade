# Broader workflow preparation — 2026-10-17

Starting commit: `938d4c6` (`feat: decomp 2 done`), clean main worktree.
The user assigned preparation, not a firmware worker run. No model job,
hardware operation, commit or push was performed.

## Readiness decision

The [broader workflow](../../../docs/broader-workflow.md) is prepared for bounded
direct-Thumb-call work as well as existing leaves. Batch 3 selects only
`fn_0000be60` and `fn_000112b0`, each owning ten bytes, with no precomputed C.
Both remain queued/unclaimed. Preparation must be reviewed and committed before
creating worker worktrees, then the user must assign the next bounded run.
This does not establish arbitrary-function or whole-image readiness.

Changes implemented:

- Trusted comparator dispatch in the queue/build handoff understands the frozen
  call-extension lock and its unchanged leaf parent. Task hashes bind complete
  assignments; explicit checks bind ranges, signatures, externs and call sites.
- Frozen batch admission pins membership, task definitions, dependency ledger,
  qualification report and qualified profile. Local admission compares selected
  verifier/parent identity to qualification. Missing contracts, changed pins or
  mismatched gate/policy fail closed. Registration alone cannot launch a task.
- Scheduling dependencies distinguish accepted bootstrap work from reviewed
  function drafts. Machine-call dependencies remain separate. Fixed external
  symbols are explicitly **not reconstructed callees**.
- A read-only ledger checks the complete 128112-byte container partition and
  distinguishes 194 declared function bytes, 174 reviewed-source bytes and
  127918 unassigned bytes. None is certified matching coverage. Unresolved
  callee, RAM, runtime, packaging, loader/device-state and recovery questions
  retain explicit evidence and next actions. Hardware remains closed.
- An evidence-backed blocker has a terminal `block` review state. It cannot be
  silently reclaimed/released to reset attempt/time limits. Batch planning
  never proposes reclaiming reviewed, blocked, submitted or claimed work.
- Current documentation/startup prompts now point to batch 3; earlier run
  instructions are historical. One additional read-only workflow document is
  exposed to workers. Model selection, CLI permissions, authentication/network
  isolation, writable mounts and compiler isolation are unchanged.

## Real compiler qualification

[qualify_calls.py](qualify_calls.py) used the existing pinned call experiment
and parent profile, under the compiler slot, 600-second supervisor and live
quota guard. All **18 controls passed** in about 252 seconds:

- Stock specimens `0x6464..0x646e` and `0x6500..0x650a` each reproduced ten bytes
  from ordinary C with external declarations, then reproduced them again from
  unchanged source in fresh builds. These are calibration specimens, not new
  worker assignments or source discoveries claimed for batch 3.
- A changed return constant produced a one-byte mismatch for each specimen.
  Omitting each side-effecting call was rejected for missing call relocations.
- All ten prior reviewed sources rebuilt unchanged with their original locks,
  reproducing all 174 owned bytes. No completed task was reclaimed.

Independent instruction review of the two final specimen ELFs confirmed the
original PUSH r4/lr, correctly targeted BL, clear-r0 and POP r4/pc sequence.
The first callee overwrites r0 from its literal and conditionally stores a byte
at RAM 0x401624; the second sets a byte at 0x400501 and clears r0. The wrappers
retain those calls and save/restore the same stack/register state. Caller return
uses and declaration uncertainty remain in the original contracts. The old
synthetic two-call controls also cover changed callee and argument behavior;
this run did not replace or relax their rules.

All compiler/comparator files and prior locks remain unchanged. New task locks
chain to the original qualified parent. Exact-range feedback is not original
compiler provenance, independent source certification, full-image linking or
permission to flash.

## Batch-3 evidence review

[ExportCallBatch.java](ExportCallBatch.java) processed the existing repaired
Ghidra project using `-readOnly -noanalysis`. It checked the full baseline hash,
known body ranges, TMode, instruction lengths and local error bookmarks, without
analysis mutation or pseudocode/C generation. [prepare_call_batch.py](../../../tools/prepare_call_batch.py)
then checked frozen inventory/evidence hashes, unique ownership, original bytes,
control flow, entry-only discovered callers and outgoing call targets. LLVM
independently decoded all exported bodies, including callee evidence.

- `fn_0000be60`: known caller 0x791c passes object pointer, zero and one in
  r0/r1/r2. The wrapper forwards them to 0xbd7c and clears r0 after the call.
  The callee uses full scalar tests, a byte-addressed object, global state and
  further calls. Its transitive effects remain unresolved; no purity or narrow
  scratch-register assumptions are granted. The wrapper must retain the call.
- `fn_000112b0`: known caller 0x10a2a ignores the result. The wrapper passes zero
  to 0xe58c, which calls 0x6008 and stores its returned byte to RAM 0x400515.
  For this input, mode-dependent logic may clear word 0x400124. The reviewed
  callee chain preserves r3 and uses r0/r1/r2 plus condition flags. Exact wrapper
  register/stack effects still require candidate review; qualifiers and original
  source declarations remain hypotheses.

The immutable packets carry full call context, callee instruction exports,
original listings, independent wrapper LLVM decode, references and provenance.
The [batch manifest](../../batches/batch-3-calls.json) records the callee contracts.
The first unassigned packet version was retained; v2 adds the already-checked
LLVM listing to worker packets. No v1 task was claimed or compiled. Final tasks
and gate use v2. No existing task definition was changed.

## Verification and budget

All **154 offline tests passed**, including real mount/credential-denial tests,
new call-lock task binding, trusted dispatch, serial ledger/unchanged-review
guards for both backends, dependency-state handling, terminal blockers,
complete-denominator checks, malformed batch/contracts, profile drift and stale
membership rejection. Existing non-failing SQLite ResourceWarnings occurred.

Local checks validate 15 task definitions: three accepted bootstrap tasks,
ten reviewed functions, two unclaimed batch-3 tasks. Runtime versions remain
Codex CLI 0.162.1 and bubblewrap 0.13.1. The previous ten source/definition/report
sets and old verifier files compare unchanged against the starting commit.
Batch-3 C files do not exist. No whole-inventory approval is inferred.

Live weekly remaining was 78% initially and 77% at final observation epoch
`1792196249.2014716`. The same assigned window resets at `1792649638`
(2026-10-22 16:13:58 Brisbane). The 45% stop / 40% reserve, two-worker ceiling,
20-minute/eight-attempt/three-non-improvement limits remain unchanged. No pause
latch was cleared, no quota window renewed and no model smoke/worker was run.
Future launches still require live checks and the separate user assignment.

## Artifact identities and limits

No vendor artifact was downloaded. Baseline source/retrieval identity remains
in [baseline.json](../../baseline.json): recorded 2026-08-14 from
https://accobrands.co.jp/wp/wp-content/uploads/Kensington-Slimblade-Pro-V4.49.zip,
128112 bytes, SHA-256 `e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.
Binary, packet, listing and compiler artifacts remain ignored local evidence.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `.decomp/direct-calls-v1/lock.json` | 3530 | `973b9272d7345924e44b5084437b05557e18731afbcea257fee37b593ac1c3bc` |
| `.decomp/pilot-armcc5-v1/lock.json` | 12387 | `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a` |
| `.decomp/next-leaves-v2/lock.json` | 10789 | `282c4bd898a44217d491dceef956452aee8f0eabba834b5c85f36ec87c92f76b` |
| `.decomp/call-batch-3-v2/lock.json` | 2934 | `f1c2f407acf8b6e620a121b99143f1aab1b5dde0c3fbbb8facfa7e7752d7cd03` |
| `.decomp/call-batch-export-v1.json` | 33924 | `4b6726002f784eba48ac0c233946bb1aa982af96fe116ba7febd94872f632207` |
| `decomp/batches/batch-3-calls.json` | 4979 | `9dc0b60e5914eb1b56e26a522587bb485198a879e8d9b917ff43a0c75f40b4de` |
| `.decomp/broader-controls-v1/report.json` | 14346 | `ef238a9db8a72a6c4ba99e69c65be233e073341b09335db7b75d9d1b9994ee36` |

The next supported action is review/commit preparation, then assign the bounded
batch-3 run from the handoff. Shared data, broader interworking/control flow,
image construction/certification and device compatibility/recovery remain later
milestone work, not hidden exclusions from the reconstruction goal.
