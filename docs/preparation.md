# Preparation status

Updated 2026-10-16. **Function workers are held.** The user's current instruction
is to resolve preparation blockers before a worker run, not to launch the earlier
exploratory pilot with those blockers deferred. [preparation.json](../decomp/preparation.json)
enforces that hold in the claim queue. Deleting the file does not enable claims.

| Preparation item | Current evidence |
| --- | --- |
| Shared runtime helper and both callers | Analysis model validated against 10,368 original-instruction cases and replayed on a second project copy. Inline words and continuation ownership corrected; firmware bytes unchanged. |
| Ghidra structural errors | Zero in the repaired copy, with zero overlapping function-body bytes. This does not approve all 776 discovered boundaries. |
| Available stock compiler calibration | Initial GCC 4.9.3 matches 2/6 fixed probes; Clang 23.1.1 matches 1/6. Three further SDK-led GCC 4.8/4.9 configurations still match only 2/6. Those attempts are stopped, not a proven exclusion of all GCC configurations. |
| Native Linux GCC lead | GCC 9.2.1 runs and reproduces the SDK-only control. The subsequent fixed stock calibration matches 2/6 ranges, so that profile is not qualified. |
| SDK provenance | 720 sized SDK symbol candidates inspected; two ARM runtime byte correspondences found in stock, zero GCC-stack whole-symbol correspondences under the entry/mode checks. No recovered-C coverage claimed. |
| ARM compiler candidate | Windows ARMCC 5.06u7 b960 starts under isolated Wine. Default selection requests standalone `compiler5`; explicit `mdk_pro` selection fails earlier with C9511E because the MDK product definition is absent. The user's existing Keil license has not been tested. Its `__fpl_dnaninf` library member exactly matches the 184-byte stock helper. |
| Production build/comparison integration | Held pending a usable, calibrated compiler/ABI configuration; the existing Clang leaf-feedback lock remains unchanged. |

Full evidence, hashes, failed attempts and reproduction are in the
[preparation report](../decomp/results/preparation/notes.md).

## Next action

**Focus on the supplied ARMCC 5 locally on Linux through Wine.** The user has
rejected remote Windows/VM compilation, purchases and requests for new trial
entitlements. The user reports an existing valid Keil license on Windows;
edition/type and suitability for this arrangement remain unknown.

The earlier missing-license result selected the standalone product. It did not
test Keil licensing. The new explicit `mdk_pro` diagnostic confirms missing MDK
product configuration, not rejection of the user's license. Obtain only the
stock `.elmap` product-definition files from the existing Keil installation's
`ARM/sw/mappings` directory into ignored `.decomp/keil-mdk/mappings`, and identify
the edition/license type. Do not request keys, `TOOLS.INI` contents or registry
dumps in chat. Then reproduce the corresponding product layout and test the
appropriate configuration; do not assume a Windows node-locked license is
portable to Wine. See the [local ARMCC investigation](../decomp/results/preparation/armcc-linux.md)
for exact evidence and next checks.

Starting the executable is not successful compilation. Stock ARM9 compilation,
linking, representative calibration and verifier qualification still follow.
Do not modify license checks, spoof host identity, fetch unofficial compiler
bundles, upload firmware or publish compiler files. Earlier GCC experiments
remain evidence, not the current requested direction or a qualified fallback.
The user-supplied `/ARMCC/` directory is ignored and remains in place. Its source
download URL has been requested and is not yet independently recorded.

The two subsequently supplied ZIPs do not establish licensed compiler access:
`arm-compiler-legacy-5.06.zip` contains Windows 5.06 update 4 build 422;
`ARMCompiler_506_Windows_x86_b960.zip` identifies 5.06 update 7 **for
Certification**, build 960. The latter shares the original folder's release/build
number but has different executable hashes and certification-specific notes.
Both sets of bundled notes require a suitable license. Neither ZIP's executables
or installer were run. Their identities and static comparisons are recorded in
the [preparation report](../decomp/results/preparation/notes.md#additional-user-supplied-zips)
and [source manifest](../decomp/results/preparation/sources.json); source URLs
remain unconfirmed. Both ZIPs are ignored and remain in place.

The SDK's 5.05 build-41 reference and the supplied 5.06 library match are leads,
not proof of the exact application compiler version. Even a usable license will
not automatically close preparation: run bounded calibration, review ABI/flags,
validate the selected compiler/linker/comparator, and version any replacement
task locks before opening the gate. Keep the current packets and lock as evidence.

The [official Keil download page](https://www.keil.com/download/product/) distinguishes
evaluation downloads from entitlement to previous versions. Its
[Lite restrictions](https://www2.keil.com/limits) exclude Arm7/Arm9/Cortex-R4.
Do not assume a free MDK-Lite download is a usable ARM9 compiler license.

After preparation passes, a separate user-assigned model/concurrency/budget
is still required before launching workers. The [pilot](pilot.md) describes
the held assignments; [the workflow](workflow.md) describes their later operation.

## Checks

Inspect configuration and the hold:

```sh
python3 tools/decomp.py check --local
```

```sh
python3 tools/decomp.py status
```

These commands validate configuration/evidence, not readiness or reconstructed
coverage. All six function tasks should show blocked. Full-image reconstruction,
dependency/recovery accounting and hardware validation remain later gates in
the [project plan](project-plan.md). No device access occurred during preparation.
