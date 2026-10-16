# Bootstrap inventory — 2026-10-16

Historical bootstrap record. The subsequent [readiness pass](../readiness/notes.md)
resolves three of the four diagnostics below in a separate project, leaving
runtime-helper modeling unresolved. Original reports and packet hashes here
remain unchanged.

Setup completed without device access or firmware-function reconstruction.
The [corrected review](#review-correction) is blocked by four saved Ghidra errors;
the initial clean structural verdict is superseded. Independent acceptance has
not occurred. The function queue stays empty and matching coverage stays unknown.

## Reproducing setup

Run from the repository root. Python 3.10+, `unzip`, `tar`, and network access
are sufficient for acquisition. No system package installation was needed.
The pinned archives install under `.decomp/tools/`; no shell profile is edited.

```sh
python3 decomp/results/bootstrap-inventory/setup.py --state .decomp --baseline decomp/baseline.json
```

```sh
python3 tools/decomp.py verify-input .decomp/stock/stock-v4.49.bin
```

The official ZIP, EXE, complete resource, and payload all match the historical
hashes in [the baseline](../../baseline.json) and
[stock-baseline.md](../../../docs/stock-baseline.md). The extractor finds the
unique length-prefixed 128,112-byte resource matching the baseline hash, at EXE
offset `0x20090a`. It does not execute the EXE. It is intentionally specific to
this baseline, not a general .NET resource-name parser.

[artifacts.json](artifacts.json) pins URLs, lengths and archive hashes. Local
`.decomp/acquisition.json` records the 2026-10-16 retrieval/verification times.
Ghidra 12.1.4 archive SHA-256 is
`ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`.
Temurin JDK 21.0.12.1+1 archive SHA-256 is
`ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94`.
Both archive digests matched upstream HTTPS release metadata. GPG verification
was not performed. Both `java -version` and `javac -version` ran successfully.
Installed archives and downloads occupy approximately 2 GB together.

Use the [release-specific Getting Started document](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/GhidraDocs/GettingStarted.md),
which requires Java 21; the development branch's Java 25 requirement does not
apply to this release. `headless.py` contains all Java settings/cache writes in
the state directory, including the launcher's XDG configuration location.
It treats logged Ghidra script errors as failures even if Ghidra exits zero.

## Import, analysis and frozen export

Ghidra 12.1.4 rejects project paths containing hidden components such as
`.decomp`. Its database therefore lives in ignored `ghidra/projects/`.
The final project is `SlimBlade-v449-bootstrap`. Earlier `SlimBlade-v449`
and `SlimBlade-v449-v5t` projects are retained only as local setup diagnostics.
Use a fresh project name and fresh export filenames when reproducing; do not
overwrite or rerun map-creation scripts against an existing prepared program.

```sh
mkdir -p ghidra/projects
```

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-bootstrap -import .decomp/stock/stock-v4.49.bin -loader BinaryLoader -processor ARM:LE:32:v5t -cspec default -loader-baseAddr 0 -noanalysis -scriptPath decomp/results/bootstrap-inventory -postScript PrepareBaseline.java -postScript MapObservedMMIO.java -log .decomp/ghidra/final-import.log
```

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-bootstrap -process stock-v4.49.bin -analysisTimeoutPerFile 300 -log .decomp/ghidra/final-analysis.log
```

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-bootstrap -process stock-v4.49.bin -readOnly -noanalysis -scriptPath 'decomp/results/bootstrap-inventory;ghidra' -postScript ExportInventory.java .decomp/inventory-review-v2.json -postScript ExportEvidence.java .decomp/evidence/bootstrap-review-v2 -log .decomp/ghidra/review-v2-export.log
```

```sh
python3 decomp/results/bootstrap-inventory/review.py decomp/baseline.json .decomp/stock/stock-v4.49.bin .decomp/inventory-review-v2.json .decomp/evidence/bootstrap-review-v2 .decomp/inventory-validation-v2.json
```

The corrected review intentionally exits **1** on the current project, after
writing a report listing the analysis errors and blocked function IDs. These
v2 paths already exist locally; select fresh paths for another export/review.
For an existing prepared project, run only these last two commands, not import
or analysis. Legacy evidence without diagnostics is rejected and must be
re-exported, not edited to add an empty diagnostic list.

The provisional `ARM:LE:32:v5` in the historical baseline is ARM-only and has
no `TMode`. The installed `ARM.ldefs` identifies `ARM:LE:32:v5t` as the mixed
ARM/Thumb language. That correction is based on the installed processor
definition and successful decoding, not an attempt to improve matching scores.
The baseline identity fields have not been changed. `default` compiler spec
is an analysis hypothesis, not identification of the original ABI/compiler.

Default release analyzers ran with Decompiler Parameter ID and Decompiler
Switch Analysis disabled, and trust in values read from writable memory disabled.
The complete effective option map is in the local export's `metadata.json`.
No pseudocode was produced. Analysis completed in about three seconds without
a timeout. Final export ran separately with `-readOnly -noanalysis`.

## Checked memory model

Ranges below have exclusive upper bounds. The flat address/file-offset model
is supported by the startup references but does not prove every region's
physical storage or loader behavior.

| Range | Mapping and evidence |
| --- | --- |
| `0x00000000–0x00002000` | Read-only non-executable unknown prefix; 1,961 bytes differ from FF, between `0x1000` and `0x1f7f`. Not a proven resident loader dump. |
| `0x00002000–0x00002020` | Read-only application metadata, not code. |
| `0x00002020–0x0001ed60` | Mixed executable code/data. Execute permission does not classify every byte as an instruction. |
| `0x0001ed60–0x0001f454` | Read-only 1,780-byte `.data` load image. |
| `0x0001f454–0x0001f470` | 28 FF trailer bytes; format purpose unresolved. |
| `0x00400020–0x00400714` | Writable post-startup `.data` copy, non-executable. |
| `0x00400714–0x00404054` | Uninitialized `.bss` block, cleared by startup; not initialized with invented reset bytes. |
| `0x4073b0`, `0x4073bc`, `0x407abc`, `0x407dbc`, `0x407efc` | Only the five observed 4-byte stack/guard anchors are mapped. Full stack extents and RAM limits remain unresolved. |

Thirteen small volatile, uninitialized, non-executable MMIO blocks cover only
directly reviewed accesses: words at `0x80001c`, `0x800020`, `0x800040`,
`0x800044`, `0x806000`, `0x806520`, `0x806524`; bytes at `0x804000`,
`0x804001`, `0x80400b`, `0x80400f`, `0x804080`, `0x804084`, `0x804088`,
`0x80408c`, `0x804094`, `0x80409c`. Evidence is the addressed listing at
`0x17998–0x179aa` and `0x17f5e–0x1800a`, with literals at `0x179b4`,
`0x18018`, `0x18024`, `0x18028`. No SDK register map was imported wholesale.

ARM vectors at `0x2020` load the reset pointer `0x2064` from `0x2040`.
At `0x20a4`, bytes `c4 f0 9f e5` load PC from `0x2170`; its value is
`0x19879`, selecting Thumb at `0x19878`. There, bytes `e6 4c` decode as
a Thumb literal load. Startup literals `0x2194–0x21a4` establish the RAM copy
and clear ranges. The exporter verifies the full database container equals
the original input byte-for-byte, not only its stored import hash.

The vector words at `0x2058` and `0x205c` are `0x2320` and `0x2300`.
Actual wrapper calls are `0x2304 -> 0x3e78` and `0x2324 -> 0x60e0`, both
ARM BLX into Thumb. Historical names for IRQ/FIQ callees are not evidence;
the conventional ARM vector positions associate IRQ with `0x2320` and FIQ
with `0x2300`. This differs from the old SDK-comparison notes' callee labels.

Independent LLVM 23.1.1 disassembly confirmed the ARM startup and wrapper
instructions and Thumb entry. Its temporary ELF is only a raw-byte wrapper
for disassembly, not a rebuilt image. Literal words must not be interpreted as
code merely because a linear disassembler emits mnemonics for them.

```sh
python3 decomp/results/bootstrap-inventory/crosscheck.py decomp/baseline.json .decomp/stock/stock-v4.49.bin .decomp/evidence/llvm-crosscheck
```

## Inventory review and limits

| Measurement | Result |
| --- | ---: |
| Discovered functions | 776: 37 ARM, 739 Thumb entries |
| Function-body union | 77,232 bytes |
| Overlapping function-body bytes | 0 |
| Bytes outside function bodies | 50,880 |
| Decoded instructions | 37,742 / 82,398 bytes |
| Ghidra-defined data | 9,940 bytes |
| Unclassified bytes | 35,774 |
| Multi-range functions | 41 |
| Bodies of at most four bytes | 34 |
| Computed-flow instructions, including returns | 68 |

All entries pass alignment, mode, containing-range and mapped-range checks.
That does not imply conflict-free analysis: the corrected diagnostic check
fails as detailed below. These checks do not approve the 776 function boundaries. The 41 multi-range
bodies need tail/literal ownership review; for example `0x1e62c` includes a
range starting at `0x1e140`, and `0x8318` has 11 ranges. ARM islands at
`0x1187c`, `0x15100` and `0x1e150` must not inherit a global Thumb setting.
Small bodies may be legitimate leaves, veneers, or false discoveries.

Prioritize unresolved spans `0x14080–0x14530`, `0xb280–0xb636`,
`0xaf2c–0xb270`, `0x6cd8–0x6fa4`, and the prefix; all exact unclassified
ranges are exported. Indirect dispatch, jump tables, RAM aliases, padding and
wireless paths remain in scope for later inventory refinement. No functions
are proposed as ready assignments: `decomp/functions.json` remains empty.

The denominator remains **128,112 container bytes**, including the 8,192-byte
prefix, or **119,920 bytes** when explicitly measuring only the transferred
payload. Neither discovery nor data classification is reconstruction progress.
The replacement device's revision and installed firmware remain unknown.

### Review correction

The initial checker counted overlaps without failing and did not reject
duplicate IDs/entry addresses. It also omitted Ghidra analysis diagnostics.
The corrected checker rejects all three ownership defects, including repeated
ranges within one function. Each failure identifies the involved rows, IDs and
addresses. Shared tails require an explicit future ownership model, not an
exception added just to pass this check.

Evidence schema 2 exports Error/Warning bookmarks, address spaces and incoming
control flow (including fallthrough). Errors block the overall review even if
no function owns the diagnostic address. An error inside a body blocks that
function; an error outside bodies identifies review candidates from incoming
flow. This attribution does not approve or extend any body boundary. Warnings
are reported separately. Missing, malformed or incompatible diagnostic metadata
fails review instead of implying a clean analysis.

A fresh `-readOnly -noanalysis` export of the existing project found:

| Error address | Saved diagnostic | Blocked function / attribution |
| --- | --- | --- |
| `0x4000` | Inconsistent instruction prototype/context (the ARM/Thumb conflict) | `fn_00003f48`, containing body |
| `0x4004` | Unable to resolve instruction constructor | `fn_00003f48`, incoming flow from `0x4000` |
| `0xa1d4` | Disassembly conflicts with defined data | `fn_0000a14c`, incoming flow from `0xa1d2` |
| `0x1e480` | Unable to resolve instruction constructor | `fn_0001e420`, incoming flow from `0x1e47c` |

There are four errors, zero warnings and zero unattributed errors. The new
report is `.decomp/inventory-validation-v2.json`, with status
`structural checks FAILED; inventory review BLOCKED` and exit code 1. The
inventory still has 776 entries and zero overlapping bytes. The unchanged
exported inventory hash and full database/input byte comparison confirm that
this correction changed reporting, not firmware bytes or function boundaries.
The saved analysis conflicts remain unresolved; functions absent from the
blocked list are not automatically approved either.

The original submitted [result.json](result.json), queue state and local frozen
evidence remain unchanged as historical snapshots. This correction supersedes
their clean structural-review implication; it does not accept the bootstrap
or launch function work. The updated exporter compiled and ran on Ghidra
12.1.4. All 29 offline tests pass, including 18 synthetic inventory controls
covering duplicates, inter/intra-function overlaps, adjacent ranges, error
attribution, warnings and missing/malformed diagnostic evidence.

Current inventory SHA-256:
`0f87e224b0701f83af0d855f17cb0fad441d0a61989f9aabe9ab7b0b6393bb61`.
Corrected review SHA-256:
`60c0538a501942f28aa575d3d2dd4d965266b4c913e06955b04bf3afdb806b7f`.
Schema-2 evidence packet hash:
`49d51cd61409fecda0f763df6aeb565e5db19a1589eea9431cf02f5c7c5c67f4`.

Archived initial structural review SHA-256 (superseded verdict):
`07d6882118f1a88b968615f14bd05835cb6c746ac8430a2f02eae1d5ecd9e9f4`.
Archived initial evidence packet hash (no diagnostics):
`c34324c72e4d13eb6b368c3b10894e5511a6c8e2ce8ec645bfd50e781b5b34a7`.
LLVM crosscheck packet hash:
`8626baf79dc0d1fe757e70c4257da28483b9604789497b2ba92984f6e3bc32e2`.

```sh
python3 tools/decomp.py hash-packet .decomp/evidence/bootstrap-review-v2
```
