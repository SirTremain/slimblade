# Agent-run preparation review — 2026-10-16

## Outcome and scope

The existing **six-function pilot** has a tested coordinator/worker operating
route. No new firmware function was decompiled, claimed, submitted or certified
during this preparation. Matching coverage remains unknown. Preparation does
not establish full-image support, the historic compiler version or safe flashing.

Work was isolated in `.worktrees/swarm-preparation` from `137edc3`, then reviewed
changes were copied into the main checkout for user review. No commit or push.
No device access, licence activation, purchases or API-billed inference.
The original function definitions, evidence packets, compiler options, verifier
implementation and lock remain unchanged.

## Compiler startup: observed resolution

The failure reported during the preceding readiness check was reproduced with
the normal outer Codex execution sandbox. ARMCC failed even at `--vsn` with
Wine's `ShellExecuteEx` startup error; it was not a compiler source rejection.

A controlled run **outside that additional outer sandbox**, still using the
unchanged pinned runner and its dedicated bubblewrap sandbox, succeeded. It
reported ARMCC **5.06 update 7 build 960**, MDK Professional **5.43**, and matched
all six fixed calibration ranges (98 bytes). Repeating the default outer-
sandbox route afterward failed again. The compatibility problem is localized
to the extra outer layer; the exact Wine/syscall cause has not been established.
Do not claim that licence replacement or altered flags resolved it.

Fresh synthetic compiler controls passed **7/7**: changed constants, signedness,
stores and literal data were detected; repeat/two-byte-aligned builds agreed;
the wrong-signature test was rejected. This supports the existing six-leaf
feedback path, not a whole-image linker or recovered-source certification.

The operational fix is an approved coordinator command outside the outer
sandbox. The existing inner compiler sandbox, serialization and genuine host
licence identity remain intact. No sudo, Windows desktop or further licence
request is needed for the demonstrated route. This is host-specific, not a
claim that the installation or licence is portable.

## Worker isolation and usage guard

The new runner mounts selected instructions and one immutable packet read-only,
plus only the assigned C file/result directory writable. It does not mount the
compiler, private prefix, queue, main checkout, calibration C or physical
devices. The worker harness gets read-only ChatGPT auth; model commands are
denied that state and network access by the inner permission profile. The
harness has networking for inference. Host configuration, plugins/apps and
worker self-delegation are disabled. Ordinary inherited-permission subagents
are not the firmware execution path.

Two actual local compatibility issues were tested and addressed:

- Codex 0.162.1 treats a direct file-write rule as a workspace directory and
  attempts reserved-directory creation beneath the C file. The inner profile
  therefore names `/workspace`; outer read-only mounts still enforce exact
  per-file writes. Actual nested sandbox tests check this, including denial of
  a fake auth fixture. The runner refuses changed Codex/bubblewrap versions.
- Arch's public CA bundle paths must be mounted alongside their symlinks.
  The initial synthetic model attempt failed workspace routing with TLS errors;
  after mounting the public CA targets, the same restricted environment worked.
  No private certificates/credentials were copied into source or logs.

One successful **gpt-6-luna synthetic turn** read two numbers and wrote the
expected JSON. It had no firmware input and did not claim a task. Live account
readings were 80% remaining before/during/after. Earlier preparation reading:
81% remaining. These are account observations, not a model-token cost estimate
or a guarantee about concurrent sessions.

The guard uses actual weekly quota RPC, not token estimates. It checks before
launch, polls while a worker/build is running and stops at 45% remaining,
preserving a five-point margin above the user's 40% reserve. Missing/stale quota,
RPC startup failures and a changed weekly window fail closed and latch a pause.
A new week does not automatically resume a run. Polling/reporting delay and
other sessions mean this is not a provider-enforced hard spending cap.

Queue ownership, unchanged task definitions, task pins and worktree base are
checked before launch. Locks limit concurrency to two workers, one process per
task and one compiler request. A persistent ledger enforces eight compiler
attempts and three consecutive non-improving attempts; the queue claim supplies
the cumulative 20-minute deadline. Independent review uses a fresh rebuild of
unchanged exact source, with a separate ten-minute bound and source/ABI review
still required. Queue acceptance remains `reviewed`, never `matched`.

## Validation and reproducibility

**123 offline tests passed**, including the existing 102 tests and new quota,
RPC, pause, subprocess-stop, mount/credential-isolation, queue-owner/deadline,
full-diff, serial-build and independent-review fixtures. These fixture tests
do not launch models or claim live firmware tasks. The real compiler replay,
real controls and real synthetic model smoke are separate integration checks;
a complete firmware worker/compile/review cycle is deliberately left to the
first assigned pilot, not presented as already performed.

The [evidence index](evidence.json) records byte counts and SHA-256 for ignored
reports generated locally on 2026-10-16; they are not downloaded artifacts and
have no external source URL. Keep local artifacts. Do not publish compiler state,
firmware binaries, listings or model session logs with the repository.

Compiler replay (coordinator; outside the additional outer sandbox, existing
inner sandbox retained; choose a fresh output suffix when repeating):

```sh
python3 decomp/results/preparation/armcc_replay.py --lock .decomp/pilot-armcc5-v1/lock.json --lock-sha256 2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a --output .decomp/swarm-calibration-escalated-01
```

```sh
python3 decomp/results/preparation/armcc_controls.py --root . --output .decomp/swarm-armcc-controls-01
```

```sh
python3 -m unittest discover -s tests -v
```

The startup diagnostic script is retained for evidence, not an instruction to
repeat licence troubleshooting. The model smoke is explicitly opt-in and
consumes usage; do not repeat it as part of offline tests.

## Handoff

Review and commit the preparation before creating fresh worker worktrees; Git
worktrees do not inherit these uncommitted changes. Use [the start prompt](../../../docs/pilot.md#start-here)
and [guarded procedure](../../../docs/swarm.md). The current policy window ends
2026-10-22 16:13:58 AEST. An expired window, a pause record, changed runtime/tool
pins or missing local artifacts blocks launch pending appropriate review/user
direction. Do not reset ledgers or loosen checks merely to start a worker.

Full inventory approval, support for calls/shared data, whole-image building,
dependency/storage accounting and later explicitly requested hardware gates
remain project milestones. They are not secretly declared solved by this pilot.
