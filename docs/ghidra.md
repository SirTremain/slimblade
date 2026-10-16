# Ghidra setup and inventory

This is the offline analysis procedure for milestone 1 of the
[project plan](project-plan.md), not a flashing or custom-firmware procedure.
Use the existing prepared project where available; import/setup examples below
are for reproduction, not instructions to repeat completed bootstrap work.

The [bootstrap run](bootstrap.md) installed Ghidra 12.1.4 and Temurin JDK
21.0.12.1+1 locally, verified official v4.49, and exported 776 discovered
functions. The later [readiness pass](../decomp/results/readiness/notes.md)
resolved three of four saved diagnostics in a separate analysis copy. The
remaining runtime-helper model also affects a caller with a silent data/code
misclassification. Inventory approval is blocked, and individual function
boundaries are not approved. Full commands, memory-map
evidence, artifact hashes and limitations are in the
[inventory result](../decomp/results/bootstrap-inventory/notes.md).

[Ghidra](https://github.com/NationalSecurityAgency/ghidra) provides disassembly,
decompilation, cross-references, types and scripting. Use an official release
archive and the Java version required by that release's GettingStarted file.
The upstream main README inspected on 2026-10-16 specifies JDK 25, while the
pinned 12.1.4 release requires JDK 21. The bootstrap result records the actual
release, archive URLs, retrieval dates, sizes, SHA-256s and Java version.

Start with the [official Ghidra beginner course](https://ghidra.re/ghidra_docs/GhidraClass/Beginner/Introduction_to_Ghidra_Student_Guide.html)
for GUI import, analysis, types, cross-references and exports. For the broader
matching-decompilation process, [Decompedia](https://decomp.wiki/) is the wiki
linked by decomp.dev. The GUI-first sequence here is a recommendation for this
raw firmware target; neither site mandates this repository's agent queue.

## Input and mapping

Use a locally obtained, extracted firmware resource, not the updater EXE, ZIP
or a modified experimental image. Verify it before import:

```sh
python3 tools/decomp.py verify-input /absolute/path/to/stock-v4.49.bin
```

Create a non-shared project under ignored ghidra/projects. Ghidra 12.1.4 rejects
hidden components such as .decomp in project paths. Import as Raw Binary
at base address zero with language ARM:LE:32:v5t, little endian, initially using
the default compiler specification as a hypothesis. Upstream
[ARM language definitions](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Processors/ARM/data/languages/ARM.ldefs)
include this processor ID and a separate APCS specification. The historical
ARM:LE:32:v5 candidate is ARM-only and lacks TMode. Neither compiler
specification identifies the actual compiler.

Disable automatic analysis for the first import. Check the
[historical anchors](stock-baseline.md) before selecting code: metadata and
vectors are different regions, reset is ARM, and the application entry changes
to Thumb. Set TMode context where supported by evidence. Define RAM and MMIO
blocks from verified mappings, mark volatile peripheral accesses, and distinguish
initialized RAM copies from uninitialized regions. Do not treat all file bytes
as executable or apply the related SDK's register map wholesale.

Record import settings and analysis options. Then run the selected analyzers,
review boundaries, switches, literal pools and unresolved indirect branches.
This is an inventory step, not a claim of complete discovery.

## Metadata export

Add ghidra/ to the Script Manager's script directories and run
[ExportInventory.java](../ghidra/ExportInventory.java) with an output path, or use
headless processing of the saved project. The following later-run example
assumes the imported program has been named stock-v4.49.bin and the output
parent exists:

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-bootstrap -process stock-v4.49.bin -readOnly -noanalysis -scriptPath ghidra -postScript ExportInventory.java .decomp/inventory-new-export.json
```

The script lists already-defined functions and all their body ranges, entry
mode, program hash and tool version. It does not invoke the decompiler, invent
function ends from the next symbol, or enqueue work. It refuses to overwrite
an existing export. Unknown TMode remains unknown. The stored program hash
identifies the imported file; it does not prove the database bytes were never
patched. The reviewer must compare exported bytes to the original input.

Pair the inventory with [ExportEvidence.java](../decomp/results/bootstrap-inventory/ExportEvidence.java)
and [review.py](../decomp/results/bootstrap-inventory/review.py), using the
[reproduction commands](../decomp/results/bootstrap-inventory/notes.md#import-analysis-and-frozen-export).
Evidence schema 2 includes saved Error/Warning bookmarks and incoming control
flow. Errors block review even outside discovered bodies; warnings remain
visible. Older packets without diagnostics must be re-exported. The reviewer
also rejects duplicate IDs, duplicate entry addresses and overlapping ranges,
including overlaps within a single function. No errors is not boundary approval.

For function assignments, export a reviewed addressed listing, nearby data,
cross-references and types following the [packet contract](workflow.md).
Pseudocode can be added when the user starts decompilation; it is not required
for inventory. Use readOnly/noanalysis when exporting a prepared project.
Those flags concern the Ghidra database, not general filesystem permissions.

The [headless documentation](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md)
describes import/process modes and scripts, and warns that a project open in
the GUI may prevent headless access. Keep one database writer. A third-party
Ghidra MCP bridge is optional; frozen packets need no bridge or running server.
