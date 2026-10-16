# Pilot readiness — 2026-10-16

Six isolated Thumb leaves are ready for bounded offline reconstruction and
compiler calibration. This implements the [assignment](assignment.md), not a
full matching campaign. No stock C was reconstructed, no agents launched, no
device accessed, no compiler installed, and no commit or push performed.

## What changed and why

Earlier readiness required solving the global dispatcher and historical
compiler before any pilot. Those remain genuine blockers for their own regions
and a full rebuild. This pass explicitly separates a **six-leaf exploratory
pilot** from that matching campaign. No global review result is relabeled as
passing, and no comparator threshold, expected bytes or function boundaries
were relaxed. Workers can now produce evidence-backed C and use exact-byte
feedback while testing a fixed candidate compiler. This may yield mismatches
because the original toolchain is unknown; mismatches are useful calibration
evidence, not an instruction to tune flags indefinitely.

The six entries/ranges are unchanged from the frozen discovery:

| Entry | Exclusive end | Bytes | Local evidence |
| --- | --- | ---: | --- |
| `0x3b48` | `0x3b64` | 28 | Register-only arithmetic/conditional flow; all branches internal |
| `0x3bb4` | `0x3bbe` | 10 | Register-only leaf; caller stores returned r0 |
| `0xe4ee` | `0xe4fc` | 14 | Two byte reads through argument pointer; narrowed r0 output |
| `0xe4fc` | `0xe512` | 22 | Four byte reads through argument pointer |
| `0xe540` | `0xe548` | 8 | Two byte writes through argument pointer |
| `0xe548` | `0xe558` | 16 | Four byte writes through argument pointer |

`ExportPilot.java` performs a read-only/noanalysis export from the existing
corrected Ghidra project. It checks baseline identity, exact bodies, every
instruction's Thumb state, no calls, no escaping direct flow, no local error
bookmarks and the final BX LR. No pseudocode is generated.
`tools/prepare_pilot.py` verifies the frozen inventory/packet and raw baseline,
checks LLVM's input wrapper contains the same bytes, verifies every independent
LLVM instruction address/word and local entry/call/data references, then freezes
six packets. Caller snippets and unknown source types are included. No observed
outside reference targets a body interior. Hidden indirect callers are not
claimed absent. Neither Ghidra names nor a blank error list substitutes for
these checks.

The original Ghidra projects, remaining error and earlier reports are preserved.
The runtime helper is **not fixed**. The global structural checker must still
exit 1 on `0x1e480`; the silently misclassified word at `0x1e364` and shared-tail
questions remain in the [quarantine ledger](../../../docs/dependencies.md).
No selected leaf calls or branches into that cluster.

## Build/compare boundary

`tools/stock_compare.py` pins the baseline, Clang/LLD executables and versions,
host libraries, Python, flags, environment, its own code and the reused
synthetic verifier implementation. It uses a fixed ARM968E-S/ARMv5TE Thumb
AAPCS/soft-float configuration; this is a **candidate**, not identified
historical provenance. AAPCS declaration hypotheses require worker evidence.
The official [Clang cross-compilation guidance](https://clang.llvm.org/docs/CrossCompilation.html)
supports explicit target/CPU selection; it does not identify Kensington's tools.

Each compile snapshots C into a fresh temporary directory, validates the AST,
builds afresh and links at the original address. A two-byte aligned Thumb entry
is supported explicitly without inserting matching padding. The complete single
executable PT_LOAD must agree with the only allocated `.text` section. Exact
length and every byte, including generated literal pools, are compared against
the original stock slice. No relocation masking, byte normalization, worker
object reuse or post-link patching occurs. Non-runtime ARM unwind/attribute
metadata is explicitly discarded; the pilot does not support unwinding/calls.

The restricted source policy rejects assembly, attributes, directives, compiler
intrinsics, calls, absolute-address casts, extra functions, globals and static
data. It is a narrow guard, not a proof of source authenticity or hostile-code
sandbox. Human/coordinator source review remains necessary. A byte-identical
range is labeled `exact-range-bytes`, always `certified_match: false` and
`matching_coverage: unknown`. No stock positive result is claimed or seeded from
hand-recovered C during preparation. Synthetic positive controls exercise the
same compiler/linker/ELF/comparison path; deliberately wrong probes test all six
real stock targets.

## Bootstrap review

The current coordinator rechecked the previous session's setup deliverables;
no second agent or human is impersonated. Queue reviewer identity is
`coordinator-pilot-readiness`. Acceptance covers each immutable original task's
setup acceptance criteria, with this addendum, not full reconstruction readiness:

- Inventory: frozen original bytes/startup evidence and corrected-project
  reproducibility checked; known global errors retained. The original clean
  structural verdict was superseded by its review correction. Only the six
  additional leaf boundaries are approved locally in this pass.
- Toolchain: SDK provenance and recorded candidates/uncertainties reviewed;
  the task requested evidence-backed candidates, not successful identification.
  No claim that Clang is the original compiler or ARMCC is required to begin.
- Verifier: the original 21 synthetic controls are rerun independently in a
  fresh output directory. This accepts the prototype setup deliverable only.
  The new range-feedback path adds separate tests and real-target rejection
  controls; it does not inherit whole-image or certification status.

Original submitted report files, task specifications and their hashes are not
edited. Six function tasks depend on these accepted setup records and are
unclaimed. A claim verifies the evidence packet, tool/baseline pins, task/lock
agreement and dependencies before printing a concrete worker build command.
The queue still never labels a worker's function `matched`.

## Validation outcome

48 offline unit tests, 8 prior readiness regression tests and all 21 original
synthetic verifier controls pass. Six deliberately wrong candidates are
rejected against the actual stock ranges. Repeated read-only Ghidra export is
byte-identical. All six claim/packet/release dry runs pass in a copied queue;
the actual queue retains six unclaimed tasks. Local preflight and whitespace
checks pass. The global structural checker still exits 1 as expected on the
quarantined diagnostic; this is not reported as a clean global inventory.

The real-target control report `.decomp/pilot-controls/checks.json` hashes to
`beeb45d92418b5fad7ef4abfa24ea0856d1bc33486c5709d19d4aa34d7ddc3b0`.
Before accepting setup records, the queue was backed up to
`.decomp/queue-before-pilot-acceptance.sqlite3`. Original report hashes remain
unchanged. The failed initial packet-export attempt (no complete packets) was
retained as `pilot-v1-failed` under ignored storage, not used as evidence.

## Reproduction

Run from the main checkout after integration. Existing output directories are
immutable; choose fresh names for repeat runs. The already prepared local pilot
does not require repeating Ghidra export or setup.

```sh
python3 tools/decomp.py check --local
```

```sh
python3 -m unittest discover -s tests -v
```

```sh
python3 -m unittest discover -s decomp/results/readiness -p 'test_*.py' -v
```

```sh
python3 decomp/results/bootstrap-verifier/selftest.py .decomp/verifier/pilot-repeat
```

```sh
python3 decomp/results/pilot-readiness/check.py --output .decomp/pilot-controls-repeat
```

The leaf exporter is reproducible without database mutation:

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-readiness-v2 -process stock-v4.49.bin -readOnly -noanalysis -scriptPath decomp/results/pilot-readiness -postScript ExportPilot.java .decomp/pilot-leaves-repeat.json
```

The export must match the frozen hash below. `prepare_pilot.py` pins the existing
export filename and inputs; a coordinator may generate a new proposal/lock and
packet directory with another output name for a deliberate rerun. Do not replace
assigned task definitions or trust hashes in place.

```sh
python3 tools/prepare_pilot.py --root . --name pilot-replay
```

Source-independent byte evidence remains ignored under `.decomp`. The packet
hashes and comparison lock hash are recorded in `decomp/functions.json`.

| Local artifact | SHA-256 |
| --- | --- |
| `.decomp/pilot-leaves.json` | `4ca31f47f191060e6d2b89f4ff3c50da8b4930aa80d6bb7625188044f9e56ed6` |
| `.decomp/pilot-v1/lock.json` | `2d9d35cce216a47e0ba0d244f51e3272bb6330ae30ca84e2a006199b9b7ab230` |

The firmware source URL, retrieval time, byte count and hashes remain in the
[acquisition record](../bootstrap-inventory/acquisition-record.json). Existing
compiler package provenance is in the [toolchain report](../bootstrap-toolchain/notes.md);
no new compiler download is claimed. See [result.json](result.json) for final
validation results and [pilot instructions](../../../docs/pilot.md) for launch.
