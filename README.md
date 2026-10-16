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

Current state: offline bootstrap completed on 2026-10-16. Ghidra and Java are
installed locally, official v4.49 input is hash-verified, and an exported
inventory contains 776 discovered functions with boundaries still unapproved.
The [readiness pass](decomp/results/readiness/notes.md) resolved three of four
Ghidra diagnostics in a separate analysis copy. A shared runtime-helper model
remains unresolved, including another caller with silently misclassified data;
inventory approval and the function pilot remain blocked.
The synthetic comparison prototype passes 21 checks. The original compiler
and matching coverage remain unknown; no firmware functions were reconstructed
and no function tasks were created. There is no stock matching build or
device-writing command in the active toolset.

- [Current goals, milestone gates and next work](docs/project-plan.md)
- [Research: Ghidra and collaborative decompilation](docs/decompilation-research.md)
- [Start and coordinate agents](docs/workflow.md)
- [Ghidra setup and evidence export](docs/ghidra.md)
- [Bootstrap results and reproduction](docs/bootstrap.md)
- [Stock baseline and outstanding questions](docs/stock-baseline.md)
- [Retired work and retained hardware notes](docs/legacy.md)

Inspect the queue with Python 3.10+; no extra packages are needed:

```sh
python3 tools/decomp.py status
```

Run the offline scaffold tests:

```sh
python3 -m unittest discover -s tests -v
```

For a later agent session, start with
[the coordinator prompt](decomp/prompts/coordinator.md). It starts from existing
bootstrap results and describes how to distribute reviewed function assignments.
Model choice stays with the agent runner; this repository has no provider/API
dependency and starts no agents automatically.

Offline analysis does not write to the device. A complete matching stock build
would be strong evidence of reconstruction accuracy, but would not make later
firmware edits or flashing risk-free.
