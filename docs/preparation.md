# Preparation status

Subsequent execution: the [six-task pilot completed](../decomp/results/pilot-run-20261016/notes.md)
with all six drafts reviewed and independently rebuilt. The preparation record
below describes the pre-launch state; expansion still needs separate review.

Updated 2026-10-16. **Preparation is complete for the first six-function agent
pilot.** No firmware worker has started. A user-assigned run and a commit containing
the preparation changes are the remaining launch steps, not another compiler
download or license request. Follow [the pilot handoff](pilot.md).

| Preparation item | Evidence and disposition |
| --- | --- |
| Shared runtime helper and both callers | Repaired analysis model agrees with 10,368 original-instruction cases and was replayed on a separate project copy. Firmware bytes unchanged. |
| Ghidra structural errors | Zero in the repaired copy, with no overlapping function-body bytes. This does not approve all 776 discovered boundaries. |
| Local compiler access | ARMCC 5.06u7 b960 runs headlessly under Wine with the supplied MDK Professional key. No Windows desktop or GUI is needed for builds. |
| Stock calibration | All six unchanged hypotheses reproduce all 98 owned bytes with fixed compiler options and strict LLD leaf layout. Fresh pinned replay also reproduces all six. |
| Build/comparison path | Versioned ARMCC lock, source/ABI policy, complete load-byte comparison, tool/reference pins, negative controls and serialized compiler access are implemented and checked. |
| Worker handoff | Six unchanged evidence packets, separately versioned task/profile pins and coordinator-owned build commands. Gate scope is restricted to these six IDs. |
| Enforced orchestration | Isolated Codex runner, two-worker ceiling, serial builds, persistent attempt limits and live weekly-quota stop; synthetic model round-trip passed. |

The [runner review](../decomp/results/swarm-preparation/notes.md) records the
fresh replay and controls. On this host ARMCC must run outside the additional
outer Codex sandbox, while retaining its existing dedicated compiler sandbox.
This operating route is tested; compiler/reference pins remain unchanged.
Use [the guarded launch/build procedure](swarm.md), not a raw inherited worker.

The [build review](../decomp/results/preparation/armcc-calibration.md) records
the evidence and limits; [earlier preparation notes](../decomp/results/preparation/notes.md)
retain the runtime repair, GCC experiments and licensing history. Those earlier
failed configurations are not instructions to repeat the investigation.

## Start the first run

Review and commit the preparation changes before creating worker worktrees:
worktrees start from a commit, not uncommitted files. No agent commit or push was
performed. Keep the ignored local artifacts; Git alone does not contain the
firmware, evidence packets, installed compiler or private license state.

Check the main checkout:

```sh
python3 tools/decomp.py check --local
```

```sh
python3 tools/decomp.py status
```

Expect local pins to pass, a ready verdict for the reviewed scope, and six
unclaimed/queued functions. No task is claimed merely by running these checks.
The [copyable startup prompt](pilot.md#start-here) uses the user's selected
weekly reserve: stop at 45% remaining, preserve 40%, at most two Luna workers.
Check its dated quota window and ask for a renewed run if it has expired.

The coordinator runs compiler requests serially and returns redacted outputs.
Do not give workers the private Wine prefix, installed license configuration
or the entire ignored artifact tree. Preserve the genuine host/adapters and
installed prefix; do not run license diagnostics concurrently with builds.
The compiler uses the host network namespace for that tested Wine environment;
build isolation is not a claim of network isolation or portable licensing.

## What this does not establish

- The exact historical compiler version is still unknown. The selected
  ARMCC5 profile is calibrated for these leaves, not proven for every function.
- Function signatures are pinned hypotheses. Workers must review callers and
  report ambiguity; byte equality does not prove the original C declaration.
- The comparator does not support calls, shared tails, external data, arbitrary
  ARM code or full-image packaging. Extend and test it before assigning those.
- Full stock reconstruction, independent source/ABI certification, whole-image
  verification and dependency/recovery accounting remain milestone work.
- The replacement mouse's firmware/hardware revision is not established.
  No device was accessed, and no result establishes safe or risk-free flashing.

These are explicit later milestones, not exclusions from the full stock
denominator. All stock code/data, including wireless paths, still require
accounting under [the project plan](project-plan.md). Matching coverage is unknown.
The [preparation gate](../decomp/preparation.json) does not authorize hardware
work or expand automatically when more tasks are added.

Any change to pinned tools, flags, sources of truth or verifier code requires
a new reviewed lock and repeated controls. Never refresh the current lock merely
to make checks pass. Preserve the old Clang lock and prior task snapshot.
