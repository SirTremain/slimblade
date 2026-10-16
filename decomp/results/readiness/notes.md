# Offline readiness pass — 2026-10-16

Three of the four original Ghidra diagnostics are resolved in a **separate
analysis project**. The fourth is understood as a nonstandard runtime-helper
call with inline data, but its control-flow/ownership model remains unresolved.
A second caller exposes a related silent misclassification. A matching
decompilation pilot is **not ready**: compiler/ABI calibration and the real
firmware verifier are also still missing.

This pass followed [the assignment](assignment.md) in `.worktrees/readiness`.
No agents were spawned, no device was accessed, no firmware C was reconstructed,
and no compiler was installed. The coordinator integrated the result files and
status notes without committing, accepting queue tasks or changing the baseline.

## Confirmed analysis repairs

The original `SlimBlade-v449-bootstrap` project and frozen evidence were kept.
`SlimBlade-v449-readiness-v2` is the corrected copy; `SlimBlade-v449-readiness-replay`
is an independent repeat from the original project. Firmware/container bytes
remain identical to the hash-locked official input.

| Location | Evidence and correction |
| --- | --- |
| `0x4000`, `0x4004` | The Thumb branch at `0x3fd2` targets `0x4000`; Thumb code at `0x3ffe` also falls through there. Independent LLVM decoding confirms the continuation through the return at `0x4024`. Replace the spurious ARM instruction with Thumb decoding. |
| `0xa1d4` | Thumb stack adjustment at `0xa1d2` falls through to bytes `f0 bd`, a return restoring the same saved registers as the function prologue. The existing 4-byte pointer definition crossed that return and two padding bytes. Remove that definition and decode only the 2-byte return; leave padding unclassified. |

Only two body ranges changed: `fn_00003f48` now spans `[0x3f48,0x4026)` and
`fn_0000a14c` spans `[0xa14c,0xa1d6)`. These are evidence-backed extensions,
not padding added to improve a match score. No other function metadata changed.
Listing/reference changes are confined to the corrected decode sites. These
repairs do not approve every semantic detail or make either function matched.

The corrected inventory has 776 functions, no overlapping body bytes, a
77,260-byte body union, 82,426 decoded instruction bytes, 9,936 defined-data
bytes and 35,750 unclassified bytes. These remain discovery metrics only.
The unchanged structural checker exits **1**, because the runtime error remains.

`RepairConfirmedAnalysis.java` hash-checks the entire input, asserts original
anchors, restricts changes to named readiness projects, disables incremental
code analysis, checks resulting instruction state and unchanged bytes, and
retires only the three repaired diagnostics. A transaction rolls back an
unexpected failure. The first experimental run tried setting context across
existing instructions and was rejected by Ghidra. That project/export was
retained only as a failed local experiment; v2 and the replay start from fresh
copies. Only the cleared seed now receives a context write.

## Remaining runtime-helper blocker

Observed instructions, independently decoded with LLVM:

- `0x1e47c` calls `0x1e4f0`, leaving LR at `0x1e480`.
- The helper's first instruction loads a word from LR and advances LR by four.
  Thus `0x1e480` is inline data, not the next instruction to execute.
- At `0x1e544–0x1e54c`, the helper selects a 3-bit field. For the local dispatch
  path, `0x1e558` computes a continuation from the advanced LR plus four times
  that selector. `0x1e55c` restores the caller's saved registers/LR, and
  `0x1e560` branches to the computed continuation.
- For the word at `0x1e480`, the nine selector fields are eight 2s and a 0,
  giving candidate continuations `0x1e48c` and `0x1e484`. These respectively
  branch into the existing saturation path and return zero.
- Another call at `0x1e360` uses inline data at `0x1e364`, currently decoded as
  a coprocessor instruction without an error bookmark. Its selector fields
  include 0, 1, 6 and 7: local continuations `0x1e368`/`0x1e36c` and internal
  helper dispatch paths also need modeling.

The generated [check.py](check.py) report computes these fields from the original
bytes and verifies call targets. It is not an execution proof, complete helper
reconstruction or approved call fixup. Function/shared-tail ownership and
state-dependent continuations still need review for `fn_0001e150`,
`fn_0001e420` and `fn_0001e4f0`. The first and third lack error bookmarks but
must not be selected for a pilot merely on that basis.

Do not mark this helper universally non-returning, force a single continuation,
clear the remaining bookmark, or relabel data as valid instructions to pass
the checker. Preserve the full evidence while designing and testing an explicit
call-site model. The next bounded analysis task is this shared runtime helper,
both callers, their inline words and continuation/stack behavior.

## Compiler and verifier readiness

`armcc` and `arm-none-eabi-gcc` are not on PATH. Clang/LLD remain available for
synthetic tests only. The [earlier compiler investigation](../bootstrap-toolchain/notes.md)
still supports ARMCC 5 as a candidate and GCC as an alternative; it does not
identify Kensington's compiler or exclude mixed library/application toolchains.

The [official Keil download page](https://www.keil.com/download/product/), checked
2026-10-16, requests a product serial number or license code for previous-version
access. The [Arm legacy compiler page](https://support.arm.com/downloads/view/ACOMP5)
returned only a JavaScript shell in the browser tool and HTTP 403 on direct
retrieval. No exact 5.05-build-41 archive, entitlement or usable installation
was established. [sources.json](sources.json) records retrieval results. Do not
interpret this as proof that a license purchase is required or that ARMCC is
the correct compiler; identify a candidate before requesting acquisition.

The existing synthetic verifier was rebuilt and all 21 controls passed with
the unchanged pinned lock. This is not a stock verifier. Remaining work:

1. Compare candidate compiler/runtime fingerprints and synthetic ABI probes
   against reviewed stock regions, then pin a justified configuration. Do not
   guess flags separately per function merely to improve byte similarity.
2. Implement original-address linking and a stock-image oracle covering calls,
   literals, shared tails and data. Add deliberate negative controls against
   actual stock ranges, independent of worker artifacts.
3. Extend that pipeline to full container assembly and exact-image comparison;
   keep copied code blobs and post-link patches out of source-recovery claims.
4. Review loader/ROM/library and device-state dependencies before considering
   the later hardware gate. None was made safe by these analysis corrections.

The next run should finish the runtime-helper model and compiler calibration,
then establish the range verifier before approving a 5–10-function pilot.
There are no new function tasks and matching coverage remains unknown.

## Reproduction and checks

Run from the main repository after integration. Close the baseline project in
the GUI before copying it. Use fresh names; do not overwrite an earlier project
or packet. These commands reproduce the changes without re-running autoanalysis.

```sh
cp -a ghidra/projects/SlimBlade-v449-bootstrap.gpr ghidra/projects/SlimBlade-v449-readiness-next.gpr
```

```sh
cp -a ghidra/projects/SlimBlade-v449-bootstrap.rep ghidra/projects/SlimBlade-v449-readiness-next.rep
```

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-readiness-next -process stock-v4.49.bin -noanalysis -scriptPath decomp/results/readiness -postScript RepairConfirmedAnalysis.java .decomp/readiness-next-repair.json
```

Only export after the repair command succeeds:

```sh
python3 decomp/results/bootstrap-inventory/headless.py --state .decomp -- ghidra/projects SlimBlade-v449-readiness-next -process stock-v4.49.bin -readOnly -noanalysis -scriptPath 'decomp/results/bootstrap-inventory;ghidra' -postScript ExportInventory.java .decomp/inventory-readiness-next.json -postScript ExportEvidence.java .decomp/evidence/readiness-next
```

The review below is expected to exit 1 with the single `0x1e480` diagnostic:

```sh
python3 decomp/results/bootstrap-inventory/review.py decomp/baseline.json .decomp/stock/stock-v4.49.bin .decomp/inventory-readiness-next.json .decomp/evidence/readiness-next .decomp/inventory-readiness-next-review.json
```

```sh
python3 decomp/results/readiness/check.py . .decomp/evidence/readiness-next-checks --tag readiness-next
```

```sh
python3 -m unittest discover -s tests -v
```

```sh
python3 -m unittest discover -s decomp/results/readiness -p 'test_*.py' -v
```

Validation: 29 existing tests and 8 readiness controls pass; the synthetic
verifier passes 21 controls. The independent project replay reproduces the
corrected inventory, audit and evidence packet exactly. All proprietary
listings, original bytes and generated artifacts remain ignored/local.

| Artifact | SHA-256 / deterministic packet hash |
| --- | --- |
| `.decomp/readiness-v2-repair.json` | `7e74321b3ffb4ccc2320de48257800d7f9a8cf0587588c304d541abf16026bd1` |
| `.decomp/inventory-readiness-v2.json` | `e6467b624c95023e9c5e6fa0c5babfdb27b8b35318b2277ab800aab47fe7d488` |
| `.decomp/inventory-readiness-v2-review.json` | `3785b5914421163ed47ac94f9baba0cae6a8c44b954fd7b300c0f99e648f6289` |
| `.decomp/evidence/readiness-v2` | `8918a09bb12f34ed1071c4cb4add900ee129c1120b8026d3876d0b2e48b54a9b` |
| `.decomp/evidence/readiness-checks` | `94b42a85a77c80c7bc932c028a47e533a08a4c22ccbf2147b0c24826fbbdb9b8` |
| Synthetic toolchain/verifier lock | `ee9aac190057fb65face3639fb1f69c1b2a9c55e1d5b405499ac648826133520` |
