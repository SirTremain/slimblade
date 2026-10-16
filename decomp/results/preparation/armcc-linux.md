# Local ARMCC 5 / Keil investigation

2026-10-16. The user requests existing ARMCC 5 on Linux, not a remote Windows
compiler, VM, purchase or new evaluation. The user reports an existing valid
Keil license on Windows. Its edition and license mechanism are unknown.

## Earlier standalone-folder observations (superseded where noted below)

- Supplied `/ARMCC/bin/armcc.exe` (Windows 5.06u7 b960) starts in the existing
  isolated Wine runtime. Its bytes have not been changed.
- The earlier `.decomp/armcc-probe-v3/output.txt` selected `product`, requested
  standalone FlexNet feature `compiler5`, and failed with C9555E / Flex error -1.
  No license was supplied. This is not a test of the user's Keil license.
- `/ARMCC/sw/mappings` contains `armcompiler.elmap`, `product.elmap` and
  `sitelicense.elmap`; it does not contain the MDK product definitions.
- Selecting `ARM_TOOL_VARIANT=mdk_pro` in a new version-only probe returns
  C9511E, `Product location: product not found`, `Product: unknown`. This
  establishes the missing product configuration. It does not establish whether
  this user owns Professional or whether their license works under Wine.
- Executable strings include Keil licensing diagnostics and `TOOLS.ini` lookup.
  These are evidence of a Keil code path, not proof that it succeeds on Linux.

Generated evidence under ignored `.decomp/armcc-probe-keil-selection/`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| output.txt | 898 | f213099a12b77d32c1c7264990fc7aae854c37156b6a07f837251fe73c6206e2 |
| command.json | 1437 | 495e76b2ea4aa78b1632457b49a9754dda53681c94126ac9167379592f312225 |

The probe uses a cleared environment, no license input, no network, no host
devices and no home directory. A fresh output name is required for reproduction:

```sh
python3 decomp/results/preparation/wine_probe.py . .decomp/armcc-probe-keil-selection-recheck --tool-variant mdk_pro
```

The script records the compiler's return code; script exit alone is not success.
The command-construction tests do not run Wine or touch hardware.

## Supplied MDK 5.43a: product configuration resolved

The user supplied `MDK543a.exe` after receiving the official direct download
link. Its 893,488,656 bytes hash to
`5702ed2093680932da3466134885b2141297099df106e5090c38f65a9510b7ca`.
The installer was **not executed**. Only `UV4/*`, `ARM/sw/*`, `TOOLS.*` and
`license_terms/*` were extracted under ignored `.decomp/keil-mdk-5.43a`.
No system installation, driver installation or activation was performed.
Artifact identities and provenance are in [sources.json](sources.json).

The genuine MDK product mappings are now present. A minimal local `TOOLS.INI`
selects the shipped `mdk_lite` configuration and the existing ordinary
`ARMCC/` compiler, mounted read-only at `Z:\keil\ARM\ARMCC`. No LIC or private
license store was supplied. This version-only probe now returns exit code 0:

```text
Product: MDK-ARM Lite 5.43
Component: ARM Compiler 5.06 update 7 (build 960)
Tool: armcc [4d365d]
```

This resolves product discovery, **not ARM9 compilation**. MDK-Lite's target
restrictions still apply. No firmware compilation or linking was performed in
this check. The certification ZIP remains a separate, unexecuted candidate.

### Computer ID investigation: repeatable with real adapters

`UV4.exe` starts in Wine 11.19 with a private Xvfb display. File → License
Management displays a generated Computer ID and an Evaluation Version entry.
The host desktop, mouse/USB nodes, home directory and private license material
are not mounted. Xvfb's GLX extension is disabled because the initial attempt
loaded host graphics support and crashed; no system graphics configuration was
changed. Both Wine and Xvfb were extracted locally, without package installation.

Initial failed probes, before the prefix repair below:

- Reopening the license dialog in the same process retained the displayed CID.
  Restarting the same persistent Wine prefix produced different CIDs on the same
  UTC date, including two launches pinned to CPU 0. CPU affinity did not resolve
  that observation. The host reports one CPU socket; Keil's multi-processor
  warning is not established as the cause here.
- Default network isolation hides the host adapters. An experimental
  `--real-adapters` diagnostic exposes actual network metadata read-only while
  blocking IP/packet sockets. Its denial checks pass, but Wine's `ipconfig /all`
  still reports no adapters and exits 1.
- [Wine 11.19's adapter implementation](https://github.com/wine-mirror/wine/blob/wine-11.19/dlls/nsiproxy.sys/ndis.c)
  opens an IPv4 datagram socket for `SIOCGIFHWADDR` and interface-flag ioctls.
  Blocking that socket also blocks local identity queries. The experimental
  filter therefore does **not** prove usable real-adapter discovery.
- [Keil documents timestamped CIDs](https://www.keil.com/support/man/docs/license/license_sul_install.asp)
  and daily changes. Different visible strings alone do not prove different
  licensed machine identities. No activation/LIC acceptance test was performed.

The user subsequently agreed to a network-enabled diagnostic, retaining the
filesystem, display and device isolation. Removing the socket filter alone did
not resolve enumeration: Linux saw three interfaces, but Wine's query still
failed. `sc query nsiproxy` reported error 1060 (service absent). Running the
standard `wineboot -u` inside this same private prefix populated the missing
Wine services. Afterwards `nsiproxy` was RUNNING and `ipconfig /all` returned 0.
This is ordinary Wine setup repair, not a licensing patch.

Two fresh complete launches after that repair, both using `--allow-network`,
reported two nonzero adapter MACs, both equal to the actual host's network
metadata, and displayed the same CID. The exact ID is retained in the ignored
screenshots and supplied to the user, not committed as host identity data:

| Local screenshot under `.decomp/armcc-wine-work/keil-gui/` | Bytes | SHA-256 |
| --- | ---: | --- |
| `screen-1792148201127649914-1.png` | 27283 | `e1337d6b04f1dfdb34e3f62c77d9701b786b20e8d33898a1969d0dd60c501a86` |
| `screen-1792148232699839685-1.png` | 27264 | `5d9f359010cf278542904d38214c5ba3120080b7ffe90df20cac87aa6b22f9c2` |

This establishes repeatability across the tested launches, not successful
license activation or guaranteed future stability. It supersedes the earlier
IDs generated with incomplete Wine configuration or hidden adapters. Do not
use those earlier IDs. No adapter identity, volume serial, compiler binary or
licensing check was changed. No activation request or contact form was submitted.

[keil_gui_probe.py](keil_gui_probe.py) preserves the diagnostic, not a production
compiler or activation runner. Its default is network-isolated and is **not**
the tested CID environment; the successful check requires `--allow-network`
and the repaired persistent `.decomp/armcc-wine-work/prefix-v2`. The experimental
[socket filter](offline_identity.py) is retained as failed-probe evidence, not
a solution. Screenshots and raw logs remain ignored under
`.decomp/armcc-wine-work/keil-gui`; never enter a key into this logging probe.
All private Wine/X sessions were stopped after inspection.

Integrated-checkout verification: all 78 offline unit tests pass, including
five new command-construction checks. Local scaffold/evidence checks pass and
all six function claims remain blocked. No commit or push was performed.

## Relevant official evidence

Checked 2026-10-16; web references, not downloaded compiler artifacts:

- [Arm's Keil diagnostic example](https://www.keil.com/support/docs/3927.htm)
  shows shared `Keil_v5/ARM/sw/mappings`, variant `mdk_pro_flex`, and feature
  `mdk_pro_compiler5`. It documents a different server-version error; that
  server-version issue was not observed locally. The product-selection example
  demonstrates why standalone `compiler5` is not an adequate Keil test.
- [Keil application note 267](https://www.keil.com/appnotes/files/apnt_267_v1.2.pdf)
  describes alternative toolchain installation below the Keil `ARM` directory
  and the `sw` mapping files. An isolated standalone folder is not the full MDK
  product layout.
- [Arm employee response about Wine](https://community.arm.com/support-forums/f/dev-platforms-forum/53436/can-we-install-keil-mdk-on-ubuntu)
  acknowledges successful user reports while stating that Wine is unsupported.
  This is not a test of this compiler build, license or target.
- The supplied compiler release notes, section 2.2, state MDK licensing is
  supported on Windows only. Unsupported Wine operation and technical failure
  are different claims; neither is proof that a Windows license is transferable.

## First supplied LIC test: C-ARM product and obsolete CPU option

Historical result; the second-key test below corrects the CPU-error diagnosis.

The user placed a key in ignored `.decomp/keil-license.txt` and explicitly asked
to test it. [keil_license_check.py](keil_license_check.py) entered that unchanged
key through the normal Add LIC control, with stdout/stderr captured in memory,
redacted diagnostic output, no raw log files and no screenshots. The small
[Win32 UI helper](keil_ui_text.c) reads ordinary dialog controls and only the
product column of the license table, never its license-code column. It does
not call or patch internal licensing routines. No vendor contact form was sent.

Observed results, recorded in [keil-license-check.json](keil-license-check.json):

- The license dialog reported that the LIC was added successfully. On a fresh
  launch its product column reads **C-ARM Compiler/Assembler Kit**. This is
  technical acceptance by the local application, not verification of the key's
  issuing source or contractual entitlement.
- ARMCC 5.06u7 b960 still reports **MDK-ARM Lite 5.43**. Compiling the synthetic
  [keil_smoke.c](keil_smoke.c) for `--cpu=ARM968E-S --thumb -O2` exits 1 with
  **C3903U**, stating that this CPU argument is not permitted. No object exists,
  so the linker is not run. No firmware reconstruction or calibration occurred.
- One default check and three explicit genuine product selectors (`mdk_basic`,
  `mdk_std`, `mdk_pro`) gave the same result. A final normal configuration check
  changed only `TOOLS.INI`'s selector from `mdk_lite` to `mdk_pro`; opening
  µVision reset it to `mdk_lite`, and all three checks still failed identically.
  Seven synthetic compile attempts total; no flags/source tuning or key changes.
- Compiler/linker SHA-256s remain identical to the recorded original files.
  The supplied key remained installed only in the ignored local Keil setup; it
  was not uninstalled or deleted. The key file and `TOOLS.INI` have mode 0600;
  the private Keil and Wine work directories have mode 0700. All test processes
  were stopped. There was no USB/HID/mouse access.

The old screenshot-capable GUI probe now refuses a setup containing an installed
LIC. The no-screenshot checker explicitly opts into that private state. This
prevents accidentally capturing the newly populated license table in later work.

[Keil identifies CARM as a discontinued compiler](https://www.keil.com/arm/carm.asp),
replaced by RealView tools. The displayed C-ARM product and unchanged Lite label
remain observations, but attributing C3903U to licensing was incorrect: the CPU
name itself was removed from this compiler. The first key was not retested with
the corrected option. Accepting a key in µVision does not establish its issuing
source or contractual entitlement. No bypass was attempted.

## Professional LIC test: headless compile and link pass

The user replaced the private file with a second key. Normal Add LIC accepted
it as **MDK-ARM Professional**, and the compiler now identifies itself as
**MDK Professional 5.43**, ARM Compiler **5.06 update 7 (build 960)**.
The initial unchanged probe still failed C3903U. A supported-CPU query returned
`5TE` but not `ARM968E-S`. The compiler's bundled release notes,
`ARMCC/sw/info/releasenotes.html`, section **SDCOMP-45000**, explicitly document
removal of the ARM968E-S processor option in 5.06 update 3 and its replacement
with `--cpu=5TE`. Its file identity is recorded in
[keil-professional-check.json](keil-professional-check.json).

Only the synthetic access probe was corrected to use that documented option;
no stock calibration flags, expected bytes or worker locks were changed.
With `--cpu=5TE --thumb -O2 -c`, the unchanged tiny C source compiled and linked
successfully under all three previously tested selectors. Every check reported
the same Professional product; this is not evidence of three different editions.
A separate fresh, default-selector `--headless-test` also produced an object and
linked image with exit codes 0, without starting µVision or Xvfb. The local
Windows compiler can therefore be invoked from the Linux command line through
Wine; no Windows desktop session is required for this tested path.

The four successful checks used temporary sandbox output, not firmware inputs.
No artifact bytes were retained or certified. Compiler/linker hashes are
unchanged. Key/config remain ignored and private (0600 inside 0700 directories);
no key contents, screenshots or raw licensing logs were saved. All test
processes were stopped. No device was accessed. The key's provenance and
contractual entitlement remain unverified; successful execution is a technical
result, not proof of either or of official Wine support.

For reproduction against the already installed license, use `--headless-test`.
This neither adds a license nor requires the Win32 UI helper:

```sh
python3 decomp/results/preparation/keil_license_check.py --root . --headless-test
```

To inspect the installed product through the UI, first build the non-secret
helper with the retained local Wine compiler, then use `--test-existing`.
`--install-and-test` is a separate explicit operation and must not be run
automatically. The default only inspects product/control metadata.

```sh
.decomp/tools/wine-11.19/usr/bin/winegcc -m64 -Wall -Wextra -o .decomp/armcc-wine-work/keil-gui/keil_ui_text.exe decomp/results/preparation/keil_ui_text.c -luser32
```

```sh
python3 decomp/results/preparation/keil_license_check.py --root . --test-existing
```

## Exact next checks

No more MDK downloads or copied mappings are needed. A repeatable CID from
the normal real-adapter environment has been obtained. Preserve this prefix
and the same real host/network configuration for any subsequent activation and
compiler tests; the earlier completely network-isolated runner is not yet a
validated licensed build environment. This diagnostic approval does not authorize
future unrelated network activity, hardware access or automatic activation.

The supplied Professional key now passes synthetic ARMv5TE compilation and
linking locally, including a headless run. Another license edition is not the
next technical blocker demonstrated by these tests. Preserve the private
configuration; do not automatically reinstall the key on future runs.

Next, use this candidate in bounded, fixed representative stock calibration,
then review ABI/flags and independently check the pinned build/comparison path.
The smoke test's `--cpu=5TE` replacement is vendor-documented compatibility, not
proof of the stock compiler's exact scheduling/optimization settings or version.
The worker gate remains closed; matching coverage is unknown. No hardware access.

## Preserved preceding GCC result

Before the user refocused this investigation on ARMCC, the bounded
[resumed calibration](resumed-calibration-plan.md) tested GCC 9.2.1 with fixed
`sdk-nolto` flags and unchanged source/comparison inputs. Exact ranges: 0x3bb4
and 0xe540; differences: 0x3b48, 0xe4ee, 0xe4fc, 0xe548. Result: 2/6, not a
qualified stock profile or a general impossibility proof about GCC.

Local report `.decomp/calibration-sdk-gcc9-stock/report.json`: 32,426 bytes,
SHA-256 `0de80fc0e9d7d6a8dda895f2c8285f2ec41950e4c87bee2a0724e4b3ef98a179`.
The separate experimental native comparator remains unintegrated in the
preparation worktree; it does not replace worker locks or open the gate.
