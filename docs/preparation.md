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
| Native Linux GCC lead | The pinned SDK stack identifies GCC 9.2.1. That official native Linux release runs and reproduces one 8-byte SDK-only control. This is not a Kensington match or a qualified stock compiler. |
| SDK provenance | 720 sized SDK symbol candidates inspected; two ARM runtime byte correspondences found in stock, zero GCC-stack whole-symbol correspondences under the entry/mode checks. No recovered-C coverage claimed. |
| ARM compiler candidate | User supplied Windows ARM Compiler 5.06 update 7 build 960. It starts under isolated Wine but refuses operation with C9555E: no license. Its `__fpl_dnaninf` library member exactly matches the 184-byte stock helper. |
| Production build/comparison integration | Held pending a usable, calibrated compiler/ABI configuration; the existing Clang leaf-feedback lock remains unchanged. |

Full evidence, hashes, failed attempts and reproduction are in the
[preparation report](../decomp/results/preparation/notes.md).

## Next action

**Linux remains the development host.** The user requested exhausting other
avenues before Windows setup. No Windows installation, purchase, activation or
hosted upload is requested by this handoff. See the
[Linux-first investigation](../decomp/results/preparation/notes.md#linux-first-investigation)
for completed experiments, exact results and limits.

The next free-toolchain question is whether GCC 9.2.1 can reproduce
representative **Kensington** code, not whether it can target this CPU: native
ARM968E-S compilation/linking now works. Before another calibration round,
identify and review a nontrivial source-backed stock/SDK correspondence and its
ABI/boundaries. Do not reopen the six stopped attempts with an arbitrary flag
search. A new bounded packet needs new evidence; the SDK-only control is not
sufficient to open the worker gate. The exact stock rebuild requirement stays.

The supplied ARMCC executable also starts on Linux through Wine, but its
missing license still prevents compilation. A legitimate entitlement covering
that compiler, target **and host arrangement** would be needed for that route.
Starting an executable does not establish supported licensing. decomp.me's
Linux configuration uses Wibo for older ARMCC releases, but that does not prove
this project's compiler version, ARM9 settings, linker or licensing works there.
Do not download unofficial compiler bundles or upload firmware to test that lead.
Do not modify license checks or publish compiler files.
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
