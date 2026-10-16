# Bounded agent runner

The coordinator can now launch and supervise **the six reviewed leaf tasks**
using the repository runner. This is not a general/full-firmware swarm.
[Preparation evidence](../decomp/results/swarm-preparation/notes.md) includes
fresh compiler controls, real isolation tests and a successful synthetic Luna
turn. No firmware worker has been launched.

## Operating boundary

Use `tools/swarm_worker.py`, not ordinary inherited-permission subagents, for
firmware workers. Each invocation starts Codex CLI inside a separate bubblewrap
mount/PID namespace. Only selected instructions, the assigned read-only packet,
one writable C file and its writable result directory are exposed. The main
checkout, compiler, licensed Wine prefix, calibration source, queue and physical
devices are absent. A worktree by itself provides none of those protections.

The harness uses the existing ChatGPT sign-in, mounted read-only in ephemeral
private state. Inner Codex permissions deny model commands access to that state
and deny command network access. Host plugins, apps, MCP configuration, API-key
environment variables and worker self-delegation are not inherited. The harness
itself needs network access for inference. This is local process isolation, not
a VM or protection against kernel vulnerabilities.

Tested host: Linux, Codex CLI **0.162.1**, bubblewrap **0.13.1**. Worker launches
reject changed versions pending isolation/smoke review. The account client uses
the documented read-only account RPC and rejects API-key authentication. This
runner does not purchase credits or use API billing.

The coordinator's compiler command must run **outside the additional outer
Codex execution sandbox**, with the normal command approval mechanism. The
unchanged compiler script still runs its own dedicated bubblewrap sandbox.
The outer layer reproducibly prevents Wine starting ARMCC on this host; no
compiler flags, firmware bytes or licence changes fix that environment issue.
The account RPC also needs its normal writable Codex state. Request approval
for these explicit coordinator commands when required; do not disable global
sandboxing, escalate workers, use sudo, or expose the licence to a worker.

## Budget and stop rules

[swarm-policy.json](../decomp/swarm-policy.json) records the user's existing
budget: retain at least 40% weekly usage and stop at **45% remaining**. Default
workers use `gpt-6-luna`, with at most two concurrently; `gpt-6.1-sol` is available
for a bounded escalation, not an automatic retry loop.

Each launch/build requires a live unambiguous weekly Codex quota reading.
While running, it polls every 10 seconds, with a 15-second RPC timeout. Missing,
stale, exhausted or changed-window readings stop the process and latch
`.decomp/swarm/PAUSED.json`. Later healthy readings do not clear the latch.
The assigned window ends **2026-10-22 16:13:58 Australia/Brisbane**; a new window
does not silently grant another run. After an explicit user resume, the
coordinator archives the pause record and updates the reviewed window/budget.
Never clear it merely to make a command run.

This is a best-effort reserve guard, not an account-wide spending cap. Service
reporting delay, in-flight requests and usage in other sessions can cause
overshoot. The 5-point margin is deliberate. Monitor the coordinator's own
usage too; the worker supervisor cannot terminate its parent Goal session.

One task has 20 minutes from its queue claim across all worker/build turns,
at most eight compiler attempts, and stops after three without improvement.
Rejections and interruptions count; a compiler-busy scheduling collision does
not. The persistent ledger prevents fresh worker turns bypassing these limits.
Do not release/reclaim a task to reset its budget. Independent source review
may follow the worker deadline; its unchanged-source rebuild is separately
bounded to ten minutes and does not grant another source-editing turn.

## Coordinator procedure

1. Review/commit preparation before creating worker worktrees. Check local
   pins and queue using [the pilot preflight](pilot.md#start-here). Confirm the
   user assigned this run; preparation and a synthetic smoke are not a request
   to launch the firmware swarm. Check live quota and the policy window.
2. Create isolated worktrees from that commit. Claim only immediately before
   launch, using the main queue. Each worker needs its own worktree and task.
3. Launch a worker turn with the command below. It creates only the task's
   allowed output paths, checks ownership/pins/budget, then ends after producing
   a candidate and notes. Monitor the returned process/session to completion.
4. Audit the entire diff and read the source. Compile through the build wrapper,
   which serializes requests and records attempts. Return only sanitized
   comparison/rejection feedback using the worker's optional `--feedback` file.
   Use a fresh run output directory for each subsequent turn.
5. On an exact candidate, inspect source provenance, ABI, effects and addressed
   evidence, then independently rebuild using `--review`. That rebuild refuses
   changed source and uses fresh output, never worker objects. It is not by
   itself an independent source/ABI review or match certification.
6. After worker processes stop, validate the report and use the existing
   submit/review transitions. Preserve blocked/expired attempts; no automatic
   requeue. Review/integrate only allowed source and notes. No automatic commit,
   push, expansion, hardware access or OpenAxis work.

The following are **coordinator examples**, executed from the main checkout.
They assume `worker-a` already owns `fn_00003b48` and its worktree exists; they
are not instructions to claim a task during preparation.

```sh
python3 tools/swarm_account.py
```

```sh
python3 tools/swarm_worker.py --root /home/tremain/Documents/slimblade --worktree /home/tremain/Documents/slimblade/.worktrees/worker-a --task fn_00003b48 --worker worker-a --model gpt-6-luna --output /home/tremain/Documents/slimblade/.decomp/swarm/runs/worker-a-01
```

```sh
python3 tools/swarm_build.py --root /home/tremain/Documents/slimblade --worktree /home/tremain/Documents/slimblade/.worktrees/worker-a --task fn_00003b48 --worker worker-a
```

```sh
python3 tools/swarm_build.py --root /home/tremain/Documents/slimblade --worktree /home/tremain/Documents/slimblade/.worktrees/worker-a --task fn_00003b48 --worker worker-a --review
```

The printed raw comparator command in old packet output documents the immutable
build contract. During the guarded swarm, use the wrapper above so quota,
attempt, claim and elapsed-time guards are applied. Never send private build
state or the entire compiler output tree to workers.

Run non-model regression tests after orchestration changes:

```sh
python3 -m unittest discover -s tests -v
```

`decomp/results/swarm-preparation/smoke_worker.py` defaults to CLI/auth/live-quota
checks only. Its optional `--model-smoke` starts a real, bounded synthetic model
turn and needs an explicitly assigned test/run budget; do not run it casually
as an offline test.

## References

The implementation follows official Codex documentation for
[noninteractive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
[permissions](https://learn.chatgpt.com/docs/permissions),
[account/rate-limit RPC](https://learn.chatgpt.com/docs/app-server) and
[CLI options](https://learn.chatgpt.com/docs/cli/reference), consulted 2026-10-16.
Actual tests on this installation take precedence over assumed CLI syntax.
