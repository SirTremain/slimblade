# Batch 3 run — resumed, one exact draft and one blocked candidate

The initial pause below is historical. The user explicitly resumed; see the
final disposition section at the end. No preparation or comparator pins changed.

User scope: fn_0000be60 and fn_000112b0 only. No other tasks assigned.

## Preflight

- Main checkout clean at preparation commit `6c82af5` before this run.
- Read AGENTS.md, project plan, preparation, broader workflow, swarm,
  workflow and coordinator/reviewer instructions.
- `python3 tools/decomp.py check --local` passed all 15 task definitions and
  local evidence/tool locks. Previous ten functions remained reviewed.
- Frozen batch `decomp/batches/batch-3-calls.json`, SHA-256
  `9dc0b60e5914eb1b56e26a522587bb485198a879e8d9b917ff43a0c75f40b4de`,
  passed local admission, including its ledger, qualification/profile locks,
  full task definitions and evidence packets.
- Runner check passed: Codex CLI 0.162.1, bubblewrap 0.13.1.
- No pause marker existed before launch. Standalone read-only quota check
  outside the outer execution sandbox reported 77% weekly remaining at
  `1792196578.366607`, reset `1792649638`, window 10080 minutes.

## Stop evidence

Separate detached worktrees were created at the preparation commit:
`.worktrees/batch3-fn_0000be60` and `.worktrees/batch3-fn_000112b0`.
Claims belong to `luna-b3-0000be60` and `luna-b3-000112b0` respectively.
Two `tools/swarm_worker.py` launches requested gpt-6-luna, but both failed
during account RPC initialization before sandbox/model launch. No inference,
compiler attempt, candidate source or worker report was produced. The runner
created only empty allowed C placeholders and result directories.

The monitored account client latched `.decomp/swarm/PAUSED.json` at
`1792196627.3261895` with reason:
`RuntimeError: live quota RPC failed; no workers should start`.
Both runner processes exited with status 1. No task attempt ledger exists.

Observed: the standalone account check succeeded with normal outer-command
approval, while the runner checks failed inside the additional outer sandbox.
This is consistent with the documented writable account-state restriction;
it is not evidence of an exhausted account or a firmware/source defect.
No retry, pause removal, window renewal or limit reset was performed.

## Required continuation

Ask the user for explicit resume before any further launch. On resume, recheck
live quota, window, claims and pins, and use normal command approval for the
coordinator runner's account-state access while retaining the worker's existing
bubblewrap and inner permission restrictions. Do not give workers elevated
permissions or private compiler state. Preserve the pause record and claim
history. The original 20-minute claim deadlines continue to apply; do not
release/reclaim to reset them. If expired, record evidence-backed blocked
reports and the terminal block review decision rather than silently granting
a fresh budget.

The tasks remain claimed, not reviewed or firmware-blocked. The pause is a
run-level guard outcome. No pins, verifier scope, previous results, hardware,
commits or pushes were changed. Matching coverage remains unknown.

## Resume and final disposition evidence

After the user's explicit resume, live quota was 77% at `1792197650.313472`,
with the same reset/window. Local evidence/tool locks and runner versions
passed again. The pause record was archived as
`.decomp/swarm/PAUSED-batch3-1792196627.json`. Normal command approval was used
for the coordinator harness/account-state access; worker bubblewrap mounts,
inner permissions and compiler isolation were unchanged. No policy/window
renewal or claim-clock reset occurred.

Two gpt-6-luna workers ran concurrently, one per assigned task. Both produced
ordinary C drafts. The coordinator audited every file and compiled serially
through `tools/swarm_build.py`:

- fn_0000be60: one candidate attempt reproduced all 10 bytes. A fresh
  unchanged-source `--review` rebuild also reproduced all 10 bytes. Independent
  source/ABI/aliasing/stack/argument/clobber/callee review is recorded in
  [its review](../fn_0000be60/coordinator-review.md). Accept as reviewed draft,
  never certified match. Source SHA-256:
  `231d95bbdfa41919cca3e728db1f273e1763df3570e1d0ece8c4ded7f1e1e455`.
- fn_000112b0: one candidate attempt differed at four of ten bytes because
  ARMCC scheduled MOVS before PUSH. Call target/relocation were correct.
  A second Luna turn received sanitized feedback, left source unchanged and
  recorded a blocker before the supervisor stopped it at the original deadline.
  [Independent review](../fn_000112b0/coordinator-review.md) confirms the mismatch
  and actual effects. Use the terminal `block` decision, not acceptance or requeue.
  Source SHA-256:
  `52a25180e6f144708e43b08c1b68aeadefa8c8730682f92769fc3d744ff33807`.

The initial pause used most of the 20-minute claim allowance. Only one compiler
attempt per task was made; neither attempt nor non-improvement ceilings were
reset. No stronger-model escalation was used. Exact candidate independent review
has its separate bounded allowance; it grants no further source-editing turns.
The blocked task is not proof of an impossible match or wrong compiler.

All 154 offline tests passed (existing SQLite ResourceWarnings did not fail
tests). No orchestration/verifier code, pin, old task/source/result, scope,
hardware, commit or push changed. No complete-image verification or callee
reconstruction is claimed. Matching coverage remains unknown.

Final queue transitions succeeded: fn_0000be60 is `reviewed` and fn_000112b0
is terminal `blocked`. Integrated source is byte-for-byte identical to each
worker candidate, and report hashes are bound by queue submission/review.
The previous ten functions remain reviewed. All worker processes and compiler
commands are terminal, with no active pause marker. Final live quota at
`1792197928.0129151` is **77% remaining**, same weekly window. No escalation,
task addition, pin change, commit, push or hardware action occurred.

The blocked source is retained only as an explicitly non-exact candidate.
Any retry requires a separately assigned budget and deliberate reconciliation;
this completed batch run does not authorize it or a subsequent batch.
