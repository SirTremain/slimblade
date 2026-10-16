# ARMCC5 calibration and leaf-build review

2026-10-16 continuation after the Professional-key test. **Prepared scope:
the six existing leaf assignments, not a whole-image firmware build.** No worker
or paid model job was launched. No hardware, activation, commit or push occurred.
The user's `fd6e659` commit was preserved. Implementation was prepared in the
isolated preparation worktree and integrated selectively into the main checkout.

## Fixed calibration

The [predeclared plan](armcc-calibration-plan.md) kept the six hypotheses in
[calibrate.py](calibrate.py), their source text, boundaries and expected bytes
unchanged. All were compiled once per documented layout experiment; there was
no C-expression search or optimization sweep. Compiler options throughout:

```text
--cpu=5TE --thumb --apcs=/interwork --fpu=SoftVFP --littleend --c99 --gnu -O2 -Ospace
```

`--cpu=5TE` is the documented replacement for the removed ARM968E-S spelling.
Thumb state is observed in the packets. The related SDK supports C99/GNU,
interworking and size preference as leads; O2 is the candidate smoke-test/default
level, not a claimed decoding of historical project XML. The six signatures use
only explicit integer types and pointers, avoiding compiler-dependent aggregate,
enum and floating-point declarations. A Clang AST check enforces the pinned
signature and restricted source subset; ARMCC actually compiles the code.

| Fixed leaf | Complete owned bytes | ARMCC5 + strict LLD result |
| --- | ---: | --- |
| `fn_00003b48` | 28 | Exact |
| `fn_00003bb4` | 10 | Exact |
| `fn_0000e4ee` | 14 | Exact, including its two-byte-aligned entry |
| `fn_0000e4fc` | 22 | Exact |
| `fn_0000e540` | 8 | Exact |
| `fn_0000e548` | 16 | Exact |

Total: 98 bytes of calibration, **not certified recovered-source coverage**.
The initial successful run is `.decomp/calibration-armcc5-v5/report.json`.
A fresh build through the final lock is
`.decomp/pilot-armcc5-v1/replay-01/report.json`. Both report 6/6 exact ranges.
No compiled object from the first run was reused for replay.

### Retained unsuccessful integration attempts

- V1 stopped before compilation on a sandbox script-path defect.
- V2 compiled every source. The Arm linker rejected a two-byte load-region
  base, padded some output regions, and its entry segment flag needed an
  Arm-specific reader. These were not silently counted as C mismatches.
- V3 used documented natural execution-region alignment. Three complete ranges
  matched, but load-region alignment still prevented the remaining layouts.
- A separate synthetic scatter test at `0x1002` rejected `ALIGN 2` with L6940E.
  No warning/error suppression or byte trimming was used.
- V4 changed only the isolated leaf linker to LLD. Its strict orphan policy
  rejected non-allocated `.debug_frame` metadata.
- V5 explicitly placed that debug metadata outside runtime allocation. All six
  ranges then matched. `.arm_vfe_header` is non-allocated compiler metadata;
  it is explicitly discarded. All allocated bytes remain subject to comparison.

The Arm-linker failures remain in `.decomp/calibration-armcc5-v2` and `-v3`;
the synthetic scatter case is `.decomp/armcc-scatter-control`. LLD is a
per-leaf layout evaluator here, **not an identified stock firmware linker**.
The eventual full-image layout/build is still unimplemented.

## Pinned comparison and coordinator review

The new [comparator](../../../tools/armcc_compare.py) and
[headless runner](../../../tools/armcc_runner.py) provide these controls:

- Fresh C-source builds only, no worker objects, assembly, intrinsics, calls,
  globals, static data, absolute-address casts or preprocessor directives.
- Fixed compiler/linker options and explicit signature hypotheses. Declaration
  changes require coordinator review, even when machine bytes would be equal.
- Entire allocated text and complete sole RX load segment compared at the
  original Thumb entry, including size and any literal bytes. No relocation
  masking, padding trimming, post-link patches or source-byte substitution.
- Object allocation/alignment checked: the leaf layout cannot silently lower
  literal-pool alignment. Runtime relocations are outside this scope and fail.
- Pins cover the original image, task definition, expected range, tool binaries,
  compiler/Wine/product-support trees, listed host libraries and verifier code.
  Pins are rechecked after a build. Changes require deliberate new versioning.
- A nonblocking prefix lock prevents overlapping compiler jobs. The coordinator
  runs them serially; a scheduling collision is not a source attempt.
- The build sandbox receives source/layout, not the reference firmware. It
  mounts no host USB nodes, home directory or display socket. Compiler/config
  files are read-only; the existing genuine-host Wine prefix is writable.
  Output is license-pattern redacted. No license key is pinned or published.

Coordinator code review and offline/real-tool controls support this limited
preparation verdict. This is **not an independent recovered-function review**.
A later reviewer must inspect worker source/ABI reasoning and rebuild from
source independently before accepting a draft. Same-UID worktrees are not a
hostile-worker sandbox: restrict worker mounts/writes in the chosen runner.
Do not expose the private prefix or license files to workers.

The host network namespace remains shared to preserve the tested Wine/adapter
environment. No firmware is uploaded. The mutable license/prefix state is
intentionally not published or treated as portable; runtime version checks
require MDK Professional 5.43 and ARMCC 5.06u7 b960. This is a pinned local
configuration, not a fully hermetic or independently portable build service.

### Controls and reproduction

Final checks: **102/102 offline tests pass, seven real-tool controls pass,
and the fresh calibration replay matches all six ranges**. The worker-facing
CLI returned 0 for the unchanged two-byte-entry example and 2 for a deliberately
wrong constant. A claim against a temporary queue copy produced the new ARMCC
command; the live queue hash was unchanged and contains no function claims.
Report sizes/hashes and results are in
[the machine-readable summary](armcc-calibration-summary.json).

The offline suite checks changed trust inputs, policy/signatures, malformed
ELF/load mappings, object alignment/relocations, prefix-lock contention and
scope-restricted queue behavior. It does not need Wine or private license files.

```sh
python3 -m unittest discover -s tests -v
```

Real ARMCC controls compile deliberate changed constants, signed loads, missing
stores and changed literal-pool data; every mutation must differ. Two repeat
cases must be equal, including a two-byte entry. A wrong return declaration
must be rejected before compilation. Reports are retained under
`.decomp/armcc-controls-v1` and `.decomp/pilot-armcc5-v1/controls-01`.
Use a new ignored directory for an explicit repeat; never overwrite evidence.

```sh
python3 decomp/results/preparation/armcc_controls.py --root . --output .decomp/pilot-armcc5-v1/controls-02
```

Replay the unchanged stock calibration through the pinned configuration:

```sh
python3 decomp/results/preparation/armcc_replay.py --lock .decomp/pilot-armcc5-v1/lock.json --lock-sha256 2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a --output .decomp/pilot-armcc5-v1/replay-02
```

Both real-tool commands are coordinator-only and need the existing local
compiler environment. They do not activate licenses, open a GUI, use a Windows
desktop, launch agents or access hardware. Do not run them simultaneously.

## Deliberate task migration and remaining work

No function task had been claimed: the live queue held only the three accepted
bootstrap rows. [prepare_armcc_pilot.py](../../../tools/prepare_armcc_pilot.py)
checked the original lock/packets, archived the previous definitions, and made
a separately versioned proposal. No previous oracle was overwritten.

The original Clang lock remains `.decomp/pilot-v1/lock.json`, hash
`2d9d35cce216a47e0ba0d244f51e3272bb6330ae30ca84e2a006199b9b7ab230`.
The ARMCC lock is `.decomp/pilot-armcc5-v1/lock.json`, hash
`2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a`.
The migration changes only task instructions, profile selection and explicit
ABI hypotheses; existing boundaries, evidence hashes and allowed paths remain.

The licensing/compiler/helper setup blockers are resolved for starting these
six tasks. The exact historical compiler version and source declarations are
not proven. Broader ABI features, calls/shared data, ARM functions, full-image
layout and packaging need separate reviewed extensions. All stock bytes remain
in the reconstruction denominator. Installed-device identity, external storage,
recovery and hardware validation retain their later gates.

Next: the user reviews/commits the preparation, then assigns models, concurrency
and a total run budget. Follow [the pilot handoff](../../../docs/pilot.md).
No additional edition/key request is needed for the demonstrated local build.
