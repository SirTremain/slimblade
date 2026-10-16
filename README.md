# SlimBlade Pro firmware decompilation

An offline workspace for reconstructing stock Kensington SlimBlade Pro firmware
before attempting Rotatrix-style changes. The eventual target is wired USB with
access to both sensors. Reconstruction should account for the whole chosen
stock image, including wireless code and data.

Current state: scaffolding only. No firmware was decompiled during this reset.
The function inventory is empty, the original compiler is unknown, and there
is no matching build or device-writing command in the active toolset.

- [Research: Ghidra and collaborative decompilation](docs/decompilation-research.md)
- [Start and coordinate agents](docs/workflow.md)
- [Ghidra setup and evidence export](docs/ghidra.md)
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
[the coordinator prompt](decomp/prompts/coordinator.md). It describes three
bootstrap assignments and how to distribute individual functions afterward.
Model choice stays with the agent runner; this repository has no provider/API
dependency and starts no agents automatically.

Offline analysis does not write to the device. A complete matching stock build
would be strong evidence of reconstruction accuracy, but would not make later
firmware edits or flashing risk-free.
