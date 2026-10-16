# Batch 2 completed: reviewed drafts, not certified matches

Run date: 2026-10-17 Australia/Brisbane. Preparation commit:
`df1957bf90973987591705fddccf541108a3dfec` (`feat: round 2`). The working tree
was clean at preflight. This report records completion of the explicitly
assigned four-task run, superseding the pre-run status in
[expansion.md](../../../docs/expansion.md). It does not authorize another run.

## Outcome

| Task | Owned bytes | Luna turns / candidate compiles | Final review |
| --- | ---: | ---: | --- |
| [fn_00013f58](../fn_00013f58/coordinator-review.md) | 26 | 1 / 1 | Reviewed; fresh unchanged-source exact rebuild |
| [fn_00013f72](../fn_00013f72/coordinator-review.md) | 8 | 1 / 1 | Reviewed; fresh unchanged-source exact rebuild |
| [fn_000154d4](../fn_000154d4/coordinator-review.md) | 22 | 4 / 4 | Reviewed; fresh unchanged-source exact rebuild |
| [fn_00018100](../fn_00018100/coordinator-review.md) | 20 | 1 / 1 | Reviewed; fresh unchanged-source exact rebuild |

Seven Luna turns, seven candidate compiles, four separate review rebuilds.
At most two workers ran concurrently, all through `tools/swarm_worker.py`;
no inherited-permission subagents or model escalation were used. All builds
were serial through `tools/swarm_build.py`, retaining the dedicated compiler
sandbox. Worker runtime summed to 262.557 seconds (overlapping wall times,
not billable usage). No task reached 20 minutes, eight attempts, or three
consecutive non-improving attempts. The last function's differing-byte counts
were 12, 12, 5, 0. Earlier failed candidates and feedback remain in ignored
local evidence; timers and attempt ledgers were never reset.

Independent coordinator review covered every changed source/report file and
addressed instruction/caller evidence, not just comparator results. In
particular, the six-byte copy preserves overlap behavior, and the byte-to-word
function preserves r3 across the callers that retain it. A worker load-order
description was corrected explicitly; the final pinned machine access order
is 1,0,2,3 despite the nonvolatile C expression order. See individual reviews
for unsigned widths, aliasing, condition flags and register effects.

All reports retain draft status with separate coordinator review metadata.
The main queue records all four as reviewed, not matched. The previous six
reviewed tasks were neither reclaimed nor changed. Total reviewed drafts are
now ten, with 174 owned bytes across the two batches; this is **not matching
coverage**. Whole-image verification is not implemented and matching coverage
remains unknown. Historical compiler/declarations, qualifiers, hidden callers,
and the replacement device's installed version remain unproven.

## Guard and provenance evidence

Preflight verified committed preparation, all local locks/packets, queue,
Codex CLI 0.162.1, bubblewrap 0.13.1, and absent `PAUSED.json` before claims.
The unchanged leaf compiler profile is ARMCC 5.06 update 7 build 960,
MDK Professional 5.43 under Wine, linked by the pinned LLD profile; it is a
candidate profile, not proven historical compiler provenance.

Live weekly quota started and ended at **78% remaining**, in the same assigned
10080-minute window resetting at epoch `1792649638` (2026-10-22 16:13:58
Australia/Brisbane). Final observed-at epoch: `1792160402.6410916`.
The 45%-remaining stop and 40% work reserve were retained. Healthy polling
continued during workers and builds; no pause latch, window renewal or resume
was needed. Integer quota readings do not imply zero usage, and the guard is
not an account-wide spending guarantee.

Artifact provenance is unchanged from [baseline.json](../../baseline.json):
source https://accobrands.co.jp/wp/wp-content/uploads/Kensington-Slimblade-Pro-V4.49.zip,
recorded retrieval 2026-08-14, baseline 128112 bytes, SHA-256
`e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.
No artifact was newly downloaded during this run. The batch-2 lock SHA-256 is
`282c4bd898a44217d491dceef956452aee8f0eabba834b5c85f36ec87c92f76b`;
the prior pilot lock and all compiler/reference pins remain unchanged.

Local reproducibility records, intentionally ignored and not published:

- `.worktrees/batch2-<task>/`: retained source and hash-locked submitted reports.
- `.decomp/swarm/runs/batch2-<task>-NN/`: prompts, events and quota checkpoints.
- `.decomp/swarm/builds/<task>/`: persistent attempt ledger, candidate builds,
  fresh `independent-review/`, and review status.
- `.decomp/swarm/feedback-batch2-fn_000154d4-*.md`: sanitized iteration feedback.

Source and reports were integrated byte-for-byte from reviewed worktrees using
patches. Submitted report hashes, identical integration, stopped workers and
unchanged-source rebuild hashes were checked. Local pin validation passed;
the offline suite passed all 136 tests, including verifier negative controls.
Python emitted non-failing SQLite ResourceWarnings. Existing pilot files,
task definitions, policy, verifier and pins were unchanged; their preparation
regression rebuilds were not repeated by reclaiming completed tasks.

No hardware was accessed. No commit or push was made. No tasks were added and
the experimental call verifier was not enabled. The run stops here; any
further batch or quota window needs a separate explicit assignment.
