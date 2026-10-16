# Ghidra setup for a later inventory run

This recipe has not been run on firmware. Neither Ghidra nor Java was found on
PATH during scaffold setup. The inventory script is supplied for the future
bootstrap task and has not been compiled against an installed Ghidra release.

[Ghidra](https://github.com/NationalSecurityAgency/ghidra) provides disassembly,
decompilation, cross-references, types and scripting. Use an official release
archive and the Java version required by that release's GettingStarted file.
The upstream main README inspected on 2026-10-16 specifies JDK 25; older
releases may differ. Pin the actual release, archive URL, retrieval date, size,
SHA-256 and Java version in the inventory result before analysis.

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

Create a non-shared project under ignored .decomp/ghidra. Import as Raw Binary
at base address zero with language ARM:LE:32:v5, little endian, initially using
the default compiler specification as a hypothesis. Upstream
[ARM language definitions](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Processors/ARM/data/languages/ARM.ldefs)
include this processor ID and a separate APCS specification. Neither identifies
the actual compiler.

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
/absolute/path/to/ghidra/support/analyzeHeadless .decomp/ghidra SlimBlade -process stock-v4.49.bin -readOnly -noanalysis -scriptPath ghidra -postScript ExportInventory.java .decomp/inventory-unreviewed.json
```

The script lists already-defined functions and all their body ranges, entry
mode, program hash and tool version. It does not invoke the decompiler, invent
function ends from the next symbol, or enqueue work. It refuses to overwrite
an existing export. Unknown TMode remains unknown. The stored program hash
identifies the imported file; it does not prove the database bytes were never
patched. The reviewer must compare exported bytes to the original input.

For function assignments, export a reviewed addressed listing, nearby data,
cross-references and types following the [packet contract](workflow.md).
Pseudocode can be added when the user starts decompilation; it is not required
for inventory. Use readOnly/noanalysis when exporting a prepared project.
Those flags concern the Ghidra database, not general filesystem permissions.

The [headless documentation](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md)
describes import/process modes and scripts, and warns that a project open in
the GUI may prevent headless access. Keep one database writer. A third-party
Ghidra MCP bridge is optional; frozen packets need no bridge or running server.
