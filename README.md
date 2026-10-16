# SlimBlade Pro firmware decompilation

A workspace for two milestones, defined in the [project plan](docs/project-plan.md):

1. Reconstruct official Kensington firmware and any necessary dependencies,
   verify an exact stock rebuild, then flash and validate it through explicit
   hardware/recovery gates.
2. Obtain the latest OpenAxis specification, add compatible rotation data
   and a button toggle between Mouse and Rotation modes. Keep processing on
   the device where feasible; bridge USB input to the host protocol as required.

Preserve stock wireless functionality where feasible. Remove it only as the
first optional feature if measured size limits require that tradeoff in the
custom firmware—not during stock reconstruction. Current work remains offline.

Current state: **prepared for a user-budgeted six-function agent pilot**.
[Start here](docs/pilot.md) for the handoff and copyable coordinator prompt.
The runtime-helper analysis has been repaired and independently replayed;
the corrected inventory has zero saved analysis errors, not blanket boundary
approval. ARMCC 5.06u7 b960 runs headlessly on Linux through Wine and reproduces
all six fixed stock calibration ranges. A new pinned comparison path replaces
the exploratory Clang profile without changing the reference bytes or packets.

No firmware workers have started. A synthetic Luna runner test passed; the
[bounded runner](docs/swarm.md) now enforces worker isolation, task limits and
a live weekly-usage stop. Small compiler probes are calibration evidence, not
integrated recovered firmware or certified matches. The comparator still provides
exact-range feedback, not a complete stock rebuild. There is no device-writing
command in the active toolset. Matching coverage remains unknown.

- [Current goals, milestone gates and next work](docs/project-plan.md)
- [Research: Ghidra and collaborative decompilation](docs/decompilation-research.md)
- [Start and coordinate agents](docs/workflow.md)
- [Preparation evidence and limits](docs/preparation.md)
- [Prepared pilot and copyable startup prompt](docs/pilot.md)
- [Stock byte accounting and unresolved dependencies](docs/dependencies.md)
- [Ghidra setup and evidence export](docs/ghidra.md)
- [Bootstrap results and reproduction](docs/bootstrap.md)
- [Stock baseline and outstanding questions](docs/stock-baseline.md)
- [Retired work and retained hardware notes](docs/legacy.md)

Inspect the queue with Python 3.10+; no extra packages are needed:

```sh
python3 tools/decomp.py status
```

Verify the local evidence and tool locks before starting a run:

```sh
python3 tools/decomp.py check --local
```

Run the offline scaffold tests:

```sh
python3 -m unittest discover -s tests -v
```

For a later agent session, start with
[the coordinator prompt](decomp/prompts/coordinator.md). It starts from existing
bootstrap results and describes how to distribute reviewed function assignments.
The optional worker runner requires the tested Codex CLI and bubblewrap on this
Linux host, using ChatGPT sign-in, not API billing. Queue/status commands do not
launch agents. A firmware run still needs an explicit user assignment.

Offline analysis does not write to the device. A complete matching stock build
would be strong evidence of reconstruction accuracy, but would not make later
firmware edits or flashing risk-free.
