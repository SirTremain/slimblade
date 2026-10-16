# Local ARMCC 5 / Keil investigation

2026-10-16. The user requests existing ARMCC 5 on Linux, not a remote Windows
compiler, VM, purchase or new evaluation. The user reports an existing valid
Keil license on Windows. Its edition and license mechanism are unknown.

## Observed facts

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

## Exact next input and checks

Ask for the Keil edition and license type, without a key. Obtain only the stock
`.elmap` files from the user's existing `Keil_v5/ARM/sw/mappings` directory
(installation root may differ), preserving filenames, in ignored
`.decomp/keil-mdk/mappings`. These are product definitions, not a replacement
for a valid license. Record provenance, byte counts and hashes when supplied.
Do not ask for a whole installation dump or expose `TOOLS.INI`/registry secrets.

After that input, reproduce the genuine MDK product layout in the isolated
runtime and select the actual edition/license mechanism. Diagnose ordinary
configuration or Wine API issues without patching licensing, generating keys,
spoofing the licensed host, or activating anything. The current probe deliberately
does not load private license material; a later license-aware runner must avoid
logging keys and identifiers. If this license is tied to the Windows installation,
report that exact limitation instead of promising that configuration will fix it.

Successful product detection is only the first check. Before worker readiness,
require compiler and linker operation for ARM968E-S, fixed representative stock
calibration, reviewed ABI/flags and an independently checked pinned pipeline.
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
