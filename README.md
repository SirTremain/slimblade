# SlimBlade Pro firmware decompilation

An offline workspace for reconstructing stock Kensington SlimBlade Pro firmware
before attempting Rotatrix-style changes. The eventual target is wired USB with
access to both sensors. Reconstruction should account for the whole chosen
stock image, including wireless code and data.

Current state: offline bootstrap completed on 2026-10-16. Ghidra and Java are
installed locally, official v4.49 input is hash-verified, and an exported
inventory contains 776 discovered functions with boundaries still unapproved.
The corrected inventory review reports four Ghidra analysis errors affecting
three functions; inventory approval is blocked pending investigation.
The synthetic comparison prototype passes 21 checks. The original compiler
and matching coverage remain unknown; no firmware functions were reconstructed
and no function tasks were created. There is no stock matching build or
device-writing command in the active toolset.

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
[the coordinator prompt](decomp/prompts/coordinator.md). It describes three
bootstrap assignments and how to distribute individual functions afterward.
Model choice stays with the agent runner; this repository has no provider/API
dependency and starts no agents automatically.

Offline analysis does not write to the device. A complete matching stock build
would be strong evidence of reconstruction accuracy, but would not make later
firmware edits or flashing risk-free.
