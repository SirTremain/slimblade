# Preparation-blocker work — 2026-10-16

**Not ready to launch workers.** The runtime analysis blocker is repaired, but
compiler calibration and its dependent production build/comparison integration
remain unresolved. The user's request supersedes the earlier limited-pilot
launch verdict. No workers, paid jobs, hardware operations, commits or pushes
were performed. Work used isolated `.worktrees/pilot-ready`; the user committed
the prior preparation as `c1d2868` during this session. Those changes were preserved.

## Runtime helper: bounded analysis repair

Baseline remains 128,112 bytes, SHA-256
`e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.
At `0x1e4f0`, the helper reads the word pointed to by LR, advances LR, classifies
register values and selects a three-bit dispatch field. It pops a caller-created
`{r4,r5,r6,lr}` frame. It does **not** return normally to the word after the BL.

| BL address | Inline word address/value | Local continuation targets | Other exit |
| --- | --- | --- | --- |
| `0x1e360` | `0x1e364`: `0x3efc7e09` | `0x1e368`, `0x1e36c` | Outer caller through saved stack PC |
| `0x1e47c` | `0x1e480`: `0x80492492` | `0x1e484`, `0x1e48c` | None selected by this inline word |

[TraceRuntime.java](TraceRuntime.java) executes the original BL/helper instructions
with Ghidra 12.1.4's modern `PcodeEmulator`, entirely offline. It tests both calls,
12 representative high-word values for each operand (including zeros, finite
values, infinities and NaNs of both signs), independent low words 0/1/0xffffffff,
two initial r5 values, and ARM/Thumb saved return addresses: **10,368 cases**.
All nine classification indices and all selectors present in the two words occur.
The trace fails if an inline data word is executed or a step limit is reached.

[runtime_model.py](runtime_model.py) is an independent instruction-derived
32-bit arithmetic model. [helper_fixup.py](helper_fixup.py) generates the Sleigh
analysis injection separately. Original execution, the Python model and executed
injected p-code agree on r0–r6, r12, SP, LR, PC, NZCV and instruction state for
all cases. Local exits restore the outer LR; outer-return exits retain the
advanced inline-word LR. Both restore the saved registers and pop 16 bytes.
This is finite test evidence, not exhaustive equivalence or recovered firmware C.
Generic selectors 4/5 are modeled from the instructions but are not selected by
either original word and are not covered by this matrix.

[RepairRuntime.java](RepairRuntime.java) installs the callfixup in a separate
analysis copy, defines the two inline words as data, removes false fallthrough,
records the observed continuation sets with jump-table overrides, decodes the
missing continuations/helper tail and updates only three function bodies.
The helper's `0x1e568` NOP remains outside executable body ownership; its bytes
remain accounted for as part of the original image/library section. The inline
words are annotated constant for this stock-image analysis, not assumed to be
immutable across updates. No universal no-return flag or single invented return
target replaces the real behavior.

The last saved `Bad Instruction` diagnostic is retired **after** those checks.
The structural review then reports 776 discoveries, zero errors, zero overlaps,
77,344 function-body bytes, 82,510 decoded instruction bytes, 9,944 defined data
bytes and 35,658 unclassified bytes. None is recovered-code coverage or blanket
boundary approval. The caller pseudocode still carries explicit injection,
manual-switch and synthetic unreachable-block warnings; it is retained locally
as diagnostic output, not presented as verified source.

Successful project: `ghidra/projects/SlimBlade-v449-runtime-v4`.
Fresh replay: `SlimBlade-v449-runtime-replay`. Both have identical inventory and
evidence hashes, unchanged firmware bytes and the same bounded delta:

- Inventory: `468be36c1cc8af5f9201bc20f1207127ddd55a1b392645183bba4d43d3eb7fd2`
- Evidence packet: `d497d1947359eac5ea340c88e6206b10843cddd586f1f761a1c71222a66f0916`
- Sleigh: `b25a99b040444233982d8631e14b60915b96319e7d68f2c973f6511338ea8230`
- Installed XML: `97c8390185d02e984db938331cb6eb29d1ffadd576375d3db8f5c7583d48c81c`
- Original traces: `2d6a0b306c1517c1cc027194b7d92e433c39748c5cde3c54dc0b8bcc492bd389`
- Injected traces: `b458af48a6c8a360d45af09e806c3290ab5f9489d5d8b70e3ddf6fe3d89cfdd4`

Failed intermediate attempts remain local: deprecated `EmulatorHelper` failed
on context initialization/interworking; modern emulation replaced it. Runtime
repair v1 failed injection type sizing, v2 failed a missing disassembly seed,
v3 revealed an over-broad inferred switch. V4 uses explicit, tested continuation
sets. No failed attempt is counted as a repair; each analysis attempt used a
fresh copy of the prior project. Original/bootstrap/readiness projects remain
unchanged. LLVM's earlier independent helper listing and the new exact library
fingerprint additionally support the original instruction interpretation.

## Compiler calibration and concrete licensing blocker

[calibrate.py](calibrate.py) compiles six fixed small C hypotheses using one
configuration per compiler, links at the original addresses and compares every
range byte and its exact length. No source-tuning iterations were performed;
one compile per probe per compiler. Output sources are ignored calibration
artifacts, not integrated firmware. Boundary/oracle/flag changes were not used
to improve scores.

| Probe | GNU Arm Embedded GCC 4.9.3, fixed `-Os` | Clang/LLD 23.1.1, existing fixed pilot flags |
| --- | --- | --- |
| `0x3b48` | Mismatch, 32 versus 28 bytes | Mismatch, 20 versus 28 |
| `0x3bb4` | Exact, 10 bytes | Mismatch, 12 versus 10 |
| `0xe4ee` | Mismatch, 14 versus 14 | Mismatch, 20 versus 14 |
| `0xe4fc` | Mismatch, 22 versus 22 | Mismatch, 22 versus 22 |
| `0xe540` | Exact, 8 bytes | Exact, 8 bytes |
| `0xe548` | Mismatch, 16 versus 16 | Mismatch, 16 versus 16 |

The GCC settings follow the related SDK's CPU/Thumb/size-optimization lead;
no LTO or runtime libraries are used for these isolated leaves. A mismatch can
reflect the source hypothesis or settings as well as compiler identity. These
tests neither eliminate GCC nor establish that ARMCC is indispensable. Two tiny
positives are insufficient to bless a whole-firmware matching configuration.
The existing Clang comparison lock and six task definitions remain unchanged.

GCC was downloaded from its official Launchpad release and extracted locally.
Its 32-bit host executable required a syscall-filter exception to run; nothing
was installed system-wide. Full commands, source hashes, tool hashes, flags and
per-range results are in `.decomp/calibration-gcc49/report.json` (SHA-256
`c5d59db6d859334a5a1e7f370c8a1abc76569c878a5e76e12642daa66e2b0faa`) and
`.decomp/calibration-clang/report.json` (`db4f2f2271be7d7a1471e3a2e51a5f00e2412d81ba0579cf7e4d4c852e01fca1`).

The user supplied `/ARMCC/`, 651 files / 449,603,774 bytes, and stated that no
ARM Compiler 5 license is available. Its release notes and subsequent executable
diagnostic identify Windows **ARM Compiler 5.06 update 7 (build 960)**. The
download URL has been requested but not independently authenticated; do not
invent it. [sources.json](sources.json) records the observed identities.
The directory remains in place and is now ignored to prevent accidental publication.

[inspect_armcc.py](inspect_armcc.py) uses LLVM archive/ELF readers, not the Arm
executables. `lib/armlib/fz_5s.l` member `dnaninf.o`, symbol `__fpl_dnaninf`, has
one 184-byte executable section `x$fpl$dnaninf` with no code relocations.
It equals **every byte** of stock `[0x1e4f0,0x1e5a8)`, including the NOP.
Section SHA-256: `fbcc23a191fe706e4f0ec0d9619b0739a38bb6c6391a4b25c512248308dfe0ae`.
This strongly identifies the runtime family, not the application compiler's
exact version. The member is prebuilt library evidence, not recovered C, and
was not substituted into a purported reconstructed image.

Wine 11.19's Arch package was downloaded through the configured repository,
its detached signature verified against the installed distro keyring, and
extracted under `.decomp/tools` only. No system install, post-install script,
sudo, registry activation or license modification occurred.
[wine_probe.py](wine_probe.py) starts the compiler inside bubblewrap with
unshared network/PID/IPC namespaces, a synthetic `/dev`, no host `/sys`, no
host home directory, read-only compiler/tool mounts and one writable local
work directory. Wine bus/menu/HTML/CLR helpers are disabled. No device or vendor
reports are exposed. This is a bounded availability probe, not yet a reviewed
production compiler runner or license configuration.

The default syscall filter prevented a usable 32-bit Wine initialization.
A fresh local prefix with the probe's own isolation retained succeeded after
the filter exception. The compiler then returned **C9555E / Flex -1**, missing
license for feature `compiler5`, before calibration. Its full diagnostic is
`.decomp/armcc-probe-v3/output.txt`, SHA-256
`f4e76e041d7e47a27617748068ac36693036def760401c2aef6dfe0f1bccddd6`.
The Windows-platform issue is therefore resolved for this probe; a Linux copy
would not resolve the demonstrated license error.

Official sources: [Keil downloads](https://www.keil.com/download/product/)
require entitlement for previous versions; [MDK-Lite restrictions](https://www2.keil.com/limits)
exclude Arm7/Arm9/Cortex-R4. The supplied release notes likewise require a
suitable toolkit license for standalone use. A legitimate trial/license covering
the candidate and ARM968E-S, or a different evidenced compiler path, needs user
direction. No purchase, activation, account access or licensing workaround was attempted.

## Additional user-supplied ZIPs

Both archives were inspected on 2026-10-16 and remain ignored in the repository
root. Download-page URLs have been requested; provenance is not yet independently
authenticated. No installer or executable from either ZIP was run.

| Archive | Release identified by bundled notes | Packaging |
| --- | --- | --- |
| `arm-compiler-legacy-5.06.zip` | ARM Compiler 5.06 update 4, build 422 | Windows executable/library tree |
| `ARMCompiler_506_Windows_x86_b960.zip` | Arm Compiler 5.06 update 7 **for Certification**, build 960 | Windows MSI, setup executable and release notes |

The first archive is older, not a Linux package or the SDK's 5.05 build-41
reference. Its `sw/info/releasenotes.html`, lines 163–173, explicitly requires
a suitable toolkit license. The ZIP comment
`db45a634af904e8452fcc0ccc3053816214606cf` resembles a source-archive revision,
but does not authenticate its origin. No separate license entitlement was found
in its filenames; bundled third-party notices and `sitelicense.elmap` are not
evidence that the user has a compiler license.

In the second name, `b960` denotes build 960, the same release/build number as
the original `ARMCC/` folder. However, its bundled notes explicitly describe
the certification variant, whereas the original folder's notes describe the
ordinary variant. The new notes, lines 142–155 and 225–230, require a suitable
toolkit/standalone license and configuration of the license file/server.

Only the MSI container, its two cabinet streams and four selected members were
extracted under ignored `.decomp/armcc-b960-static-hCciug/`, using archive
readers, without installation. PE version resources identify the compiler and
linker members. Their whole-file hashes differ from the original folder's
executables, so these packages are recorded separately. The selected
`fz_5s.l` member is byte-identical to the original folder's library, preserving
the earlier exact runtime-helper fingerprint. This does not prove exact
application compiler identity or compiler interchangeability.

[sources.json](sources.json) records archive sizes, SHA-256s, release-note
identities, selected member identities and unknown source URLs. Neither ZIP
demonstrates a usable license or closes compiler calibration. The earlier
C9555E/Flex -1 result applies to the original folder's executable; it is not
reported as a test of these unexecuted ZIPs.

## Linux-first investigation

The user's latest instruction prioritizes alternatives before Windows. All work
below was local Linux/offline analysis after public artifact retrieval. No
device access, paid jobs, license activation or uploads to decompilation services.
The original worker task definitions, expected bytes, boundaries and Clang lock
were left unchanged.

### Source-backed GNU comparisons

[The experiment plan](gcc-experiment-plan.md) predeclared three comparisons.
[gcc_sdk_probe.py](gcc_sdk_probe.py) extracts the SDK's four unaligned read/write
utility bodies from recorded Git history, changes linkage/name for measurement,
and retains forced inlining inside the 32-bit reader. Its two clock hypotheses
are unchanged. The source correspondence to Kensington is a hypothesis, not
confirmed original source. SDK Makefile flags and its `armgcc_4_8` directory
motivated the configurations; no register forcing, assembly or oracle edits.

| Configuration | Exact stock ranges | Other results |
| --- | --- | --- |
| GCC 4.9.3, SDK bodies, no LTO | 2/6 | `3b48`: 32/28 bytes, 29 differing; `e4ee`: 10/14, 11 differing; `e4fc`: 22/22, 14 differing; `e548`: 16/16, 4 differing |
| GCC 4.9.3, SDK bodies, LTO | 2/6 | Identical measured range outputs to no LTO |
| GCC 4.8.4 20140725, SDK bodies, no LTO | 2/6 | `3b48`: 32/28 bytes, 22 differing; `e4ee`: 10/14, 11 differing; `e4fc`: 22/22, 13 differing; `e548`: 16/16, 4 differing |

The two exact ranges remain `0x3bb4..0x3bbe` and `0xe540..0xe548`.
The three-run experiment stopped as planned. Compiler drivers, subtools,
sources, flags, commands, outputs and mismatches are recorded locally:

| Report under `.decomp/` | SHA-256 |
| --- | --- |
| `calibration-sdk-gcc49-nolto/report.json` | `83f205f3379c503ac788628d7fc80b309274870dcdbd9a37c294795dd9dc15ae` |
| `calibration-sdk-gcc49-lto/report.json` | `857b4de6f9c9c2077fdb918aa0190cf9339fd59248168109a09e34f0fd81313f` |
| `calibration-sdk-gcc48-nolto/report.json` | `e72bdb1d830987f3916c64f200dc66a41e7525376519d30509b611893923a47c` |

The old 32-bit Linux compilers needed non-root execution outside the tool's
syscall sandbox; the sandbox otherwise terminates even their version command.
Nothing was installed system-wide. These failures/successes are not license tests.

### SDK binary provenance

[inspect_sdk.py](inspect_sdk.py) validates four downloaded artifacts against the
tree's Git blob identities and sizes at upstream commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`. Local SHA-256 identities and source
URLs are in [sources.json](sources.json). It checks full sized symbols of at
least 8 bytes, with exact stock bytes, discovered entry and matching ARM/Thumb
state; this is fingerprinting, not source recovery or boundary approval.

The GCC stack ELF's `.comment` identifies GCC 9.2.1 20191025, release
`9-2019-q4-major`, revision 277599. Its 268 sized candidate symbols yield no
exact stock correspondences under those checks. The ARM app map identifies
ARM Compiler 5.05 build 41; its 452 sized symbol candidates yield:

| SDK symbol/address | Stock range | Exact bytes |
| --- | --- | --- |
| `_dfltu` at `0x31f54` | `0x1e4c4..0x1e4f0` | 44 |
| `__fpl_dnaninf` at `0x320f8` | `0x1e4f0..0x1e5a8` | 184 |

Independent `cmp` checks of both raw ranges pass. The latter spans multiple
stock analysis bodies and is not one approved Ghidra function. It repeats the
earlier ARMCC 5.06 library fingerprint; the former adds a second runtime lead.
Neither proves which compiler/version generated the application. No complete
pilot pattern occurs in the GCC stack ELF, ARM stack bin or ARM app bin.
Relocations, addresses and source changes limit what these nonmatches imply.

The retained fingerprint report is `.decomp/sdk-fingerprint-v3/report.json`,
SHA-256 `7bb4ce74dd024f6e627c096b6a0fc7c916e8830cf27f851d5dcb6d712e01f4c9`.
Earlier v1/v2 development reports remain local; v3 adds parser input validation.

### Native GCC 9.2.1 control

The SDK metadata provided a concrete newer compiler lead. The official native
x86-64 Linux archive is extracted only under `.decomp/tools/`. A separately
declared, single SDK-only control uses the non-profiling list layout from
`co_list.h` and hypothesizes initialization of its two pointers to null.
Its implementation is not supplied SDK source and is not a stock reconstruction.
[gcc_sdk_control.py](gcc_sdk_control.py) compiles/links it for ARM968E-S Thumb
at SDK `co_list_init` address `0x58f4`: **8/8 bytes exact**, one attempt, no tuning.
It runs inside the ordinary sandbox, without Wine, sudo or license configuration.

Report `.decomp/calibration-sdk-gcc9-control/report.json`, SHA-256
`0cb2aa1039e08a85beff7e7c057fe7335e99d62846ef8ebbe9ddbd4d84fab9d4`.
This proves native tool execution and one trivial SDK control only. It does not
qualify GCC 9 for Kensington or restart the exhausted six stock attempts.

### How decomp.me runs ARMCC

Read-only inspection of decomp.me revision
`6056cf56b3bf4f1cfcf2496fe97f83cc09b08010` found its
[Linux compiler list](https://github.com/decompme/decomp.me/blob/6056cf56b3bf4f1cfcf2496fe97f83cc09b08010/cromper/compilers/compilers.linux.yaml)
includes ARMCC 4.x and 5.04 build 82. Its
[compiler adapter](https://github.com/decompme/decomp.me/blob/6056cf56b3bf4f1cfcf2496fe97f83cc09b08010/cromper/cromper/compilers.py)
uses Wibo to run `armcc.exe`, with a default MPCore/3DS configuration and
compile-only output. This is evidence that a Windows desktop is not inherently
required, **not** evidence of the needed ARM9/compiler/linker/entitlement setup.
The hosted compiler API returned HTTP 403; no hosted compiler was exercised,
no unofficial compiler pack downloaded and no firmware/source uploaded.

### Remaining decision gate

Linux-first stays in effect. A next GNU stock calibration packet must first
establish a nontrivial source-backed stock correspondence and reviewed ABI and
boundaries; new compiler metadata alone does not justify endless retries of the
same leaves. Keep GCC 9 available as a candidate, not the production compiler.
The licensed Linux/compatibility-layer ARMCC route remains separate and unproven.
No evidence currently justifies declaring all Linux avenues exhausted or moving
development to Windows. Exact stock reconstruction remains the target; a
functionally similar GCC image is not substituted for that requirement.

## Gate, tests and next work

[preparation.json](../../preparation.json) disables function claims and status
shows all six tasks blocked without editing task definitions or their queue
records. Missing/malformed gate files fail closed. Bootstrap acceptance remains
historical setup acceptance, not proof of compiler readiness. Configuration
checks print the hold; their exit code still means configuration validity only.

70 offline scaffold tests pass, including missing/false/malformed launch gates,
helper-model negative controls for register, flag, stack and return changes,
and 13 SDK extraction/parser controls using synthetic inputs only.
The 10,368-case original/injected/model comparison and two independent analysis
copies pass the bounded delta checker. Matching coverage remains unknown.

Next requires a usable, legitimate compiler candidate, representative bounded
calibration and source/ABI review. Then pin and independently validate its
compiler/linker/build feedback path, version any changed task locks, and review
the gate before asking for a worker run/budget. The full-image serializer,
complete dependency/storage reconstruction and all hardware/recovery gates
remain later work; none is claimed complete here.

## Reproduction

Commands run from the main checkout with ignored evidence retained. Use fresh
output names; scripts refuse to overwrite evidence. To audit existing successful
analysis and all execution comparisons without running Ghidra:

```sh
python3 decomp/results/preparation/check.py . .decomp/runtime-check-recheck.json
```

```sh
python3 decomp/results/preparation/check.py . .decomp/runtime-replay-recheck.json --tag runtime-replay
```

To regenerate the analysis p-code and original/injected traces on a read-only
prior Ghidra project:

```sh
python3 decomp/results/preparation/helper_fixup.py .decomp/runtime-fixup-recheck
```

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-readiness-v2 -process stock-v4.49.bin -readOnly -noanalysis -scriptPath decomp/results/preparation -postScript TraceRuntime.java .decomp/runtime-original-recheck.json
```

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-readiness-v2 -process stock-v4.49.bin -readOnly -noanalysis -scriptPath decomp/results/preparation -postScript TraceRuntime.java .decomp/runtime-injected-recheck.json .decomp/runtime-fixup-recheck/runtime.sleigh
```

```sh
python3 decomp/results/preparation/runtime_model.py .decomp/runtime-original-recheck.json --injected .decomp/runtime-injected-recheck.json
```

For a new analysis replay, copy the closed `SlimBlade-v449-readiness-v2.gpr`
and `.rep` to a **new** `SlimBlade-v449-runtime-*` project under ignored
`ghidra/projects`, then run `RepairRuntime.java` with the generated XML and
a fresh output directory; export with the original inventory/evidence scripts
and rerun their structural review. Never apply repairs to the baseline project.
The successful projects/evidence above remain the pinned audit targets.

Static user-supplied library fingerprint:

```sh
python3 decomp/results/preparation/inspect_armcc.py . .decomp/armcc-static-recheck
```

The Wine version probe can be repeated with a fresh output directory after
reviewing its narrow sandbox. It does not discover or activate licenses:

```sh
python3 decomp/results/preparation/wine_probe.py . .decomp/armcc-probe-recheck
```

No compiler probe or analysis artifact is a flashing image.

To repeat the static SDK fingerprint against the retained, hash-checked downloads:

```sh
python3 decomp/results/preparation/inspect_sdk.py --root . --output .decomp/sdk-fingerprint-recheck
```

To reproduce the single SDK-only GCC 9 control with the retained native toolchain
(not a new stock matching attempt):

```sh
python3 decomp/results/preparation/gcc_sdk_control.py --root . --output .decomp/calibration-sdk-gcc9-control-recheck
```

The three stopped stock experiments are reproducible with `gcc_sdk_probe.py`;
their complete argument lists and tool identities are preserved in the local
reports above. Do not turn reproduction into an unbounded tuning campaign.
