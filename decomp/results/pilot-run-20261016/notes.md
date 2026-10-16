# Six-leaf agent pilot — 2026-10-16

## Result

All six existing function tasks are **reviewed** in the coordinator queue.
Each worker-authored C candidate was independently rebuilt from unchanged source
through the pinned ARMCC5/LLD pipeline and reproduced its complete assigned
range. Combined range size: **98 bytes**. This is not certified recovered-source
coverage, a complete firmware image, or evidence of safe flashing.

| Task / coordinator review | Bytes | Candidate compiles | Independent rebuild |
| --- | ---: | ---: | --- |
| [fn_00003b48](../fn_00003b48/coordinator-review.md) | 28 | 2 | Exact |
| [fn_00003bb4](../fn_00003bb4/coordinator-review.md) | 10 | 1 | Exact |
| [fn_0000e4ee](../fn_0000e4ee/coordinator-review.md) | 14 | 2 | Exact |
| [fn_0000e4fc](../fn_0000e4fc/coordinator-review.md) | 22 | 2 | Exact |
| [fn_0000e540](../fn_0000e540/coordinator-review.md) | 8 | 1 | Exact |
| [fn_0000e548](../fn_0000e548/coordinator-review.md) | 16 | 1 | Exact |

The predicate needed one branch/return-layout revision. Both readers needed
one revision from OR-based composition to the original arithmetic grouping.
No compiler options, expected bytes, boundaries, type locks or verifier rules
were changed to obtain these results. Workers had no access to calibration C.
No inline assembly, instruction blobs, patches, stubs or omitted behavior were
accepted as recovered C.

## Execution and budget

- Base commit: `43e206115470a6c8b069311db2bb08718439b1bb`.
- Nine bounded `gpt-6-luna` turns, at most two concurrently, through the isolated
  repository runner. No native inherited-permission subagents or Sol escalation.
- Nine actual candidate compilations plus six fresh independent rebuilds,
  serialized through `tools/swarm_build.py`. Ten candidate ledger entries include
  one quota rejection before any compiler process launched.
- The quota guard paused on a reset timestamp inconsistent with the pinned
  window. Its mismatching value was not retained; the next read again reported
  the original window. No actual weekly reset is established by this event.
- The user explicitly requested resume. The pause was archived, not silently
  cleared. Original claims, deadlines and attempt ledgers were preserved; no
  task was released/reclaimed to reset a budget. All candidate phases completed
  within their original 20-minute limits, including pause time. Independent
  unchanged-source rebuilds used the separately bounded review phase.
- Starting weekly quota: **80% remaining**. Final checked reading:
  **79% remaining**, same reset timestamp `1792649638`. These are reported
  account readings, not a monetary cost or isolation from other-session usage.
  The 45% stop / 40% work reserve was unchanged.

Private checkpoints, model logs, build evidence and the archived stop remain in
ignored `.decomp/swarm/`. Worktrees remain in ignored `.worktrees/pilot-<task>`.
No hardware was accessed, no additional function tasks were created, and no
commit or push was performed. No agents remain running for this pilot.

## Review and validation

The coordinator reviewed addressed instruction evidence and callers separately
from worker narratives, audited all changed/untracked paths, checked C widths,
signedness, shifts, pointer access and side effects, and invoked a fresh
unchanged-source rebuild for every candidate. Source and comparison hashes are
in each coordinator review. Original worker-stage reports are retained with an
added coordinator result; generic model labels or unmeasured timing fields in
those snapshots are not used as authoritative accounting.

All **123 offline tests passed**. Local evidence/tool pins passed before launch
and again during final validation. The prior seven-control compiler report
was hash-checked unchanged, not rerun or described as new control execution.
Its SHA-256 remains
`cb90467dd097aa6393f0e543b86bc67f46f6ea555096f9d3cda869413cdaae1e`.
The compiler lock remains
`2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
Integration copies only reviewed C and textual reports; firmware bytes,
generated listings, object files and compiler/licence state stay ignored.

## Limits and next decision

The source-level declarations, const/volatile qualifiers, original compiler and
undiscovered callers are still hypotheses. Exact fixed-profile output supports
these bounded drafts but is not source/ABI or whole-image certification.
Pointer-domain and wider-firmware dependency questions remain open. Matching
coverage is **unknown**; 98 bytes is not a full-firmware progress percentage.

This assigned six-task run is complete. Do not automatically requeue these
functions or expand the swarm. Further work needs a separately assigned scope
with reviewed boundaries/dependencies and any necessary verifier extension.
Review and commit the integrated sources/reports separately if desired; no
OpenAxis implementation or hardware action follows automatically.
