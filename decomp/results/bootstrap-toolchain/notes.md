# Compiler investigation — 2026-10-16

The original Kensington compiler, version, ABI, libraries and link settings
remain **unknown**. No proprietary compiler was downloaded or installed.
The setup uses Clang/LLD only for synthetic verifier tests.

## Observed evidence

The historical SDK provenance identifies the public
[Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk), commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`. Six build files were read directly
from repository commit `ea2ee1dd6f47ab414180b1b4e6ea375caef489d7`; the SDK was
not restored into the active tree and no SDK program was run. File sizes,
SHA-256s, original URLs, acquisition method and date are in
[sources.json](sources.json). The historical acquisition date was 2026-08-14;
the new inspection/retrieval date is 2026-10-16.

The freshly downloaded upstream
[boot linker map](https://gitee.com/beken-corp/bk3633_ble_sdk/raw/0a461f8ed4a4f17ff6889d6f9d34e521b92b8243/SDK/projects/app_2.4g/boot_usb/lst/bk3633_boot.map)
is 29,259 bytes, SHA-256
`126722c2df4c6e6385839513e4f27c4e81743b7304ba8ac75fc6266413936985`.
Its first line identifies `ARM Compiler 5.05 (build 41)` and `armlink`.
It lists `mc_5.l` runtime members including integer division and memory-copy
helpers. This identifies the **related SDK boot artifact**, not SlimBlade.

The SDK mouse project's Makefile names `arm-none-eabi-gcc` and
`arm-none-eabi-gcc-ar`; flags include `-Os`, `-mcpu=arm968e-s`, `-march=armv5te`,
`-mthumb`, `-mthumb-interwork`, `-flto`, `-fno-strict-aliasing`,
`-fgnu89-inline`, and `-ffast-math`. It links a prebuilt stack with
`--just-symbols=.../bk3633_stack_gcc.elf`. No GCC release number is pinned.
This permits a mixed-source/prebuilt-library toolchain; one compiler for all
image bytes must not be assumed.

The mouse and USB-boot `.uvproj` files identify `ARM-ADS`, an ARM9E little-endian
target, interworking enabled and scatter files. Mouse `MiscControls` is `--gnu`;
USB-boot uses `--c99`. `--gnu` is a compatibility flag, not evidence that this
Keil project used GCC. Numeric project optimization/Thumb settings have not
been translated into assumed command-line flags. Project files do not pin the
compiler build used by Kensington.

The related SDK scatter file starts the application at `0x25b00`, RAM data at
`0x400800`, and has additional storage near `0x812800`. Its GNU linker script
uses RAM at `0x400f00`. Both differ from the freshly verified SlimBlade startup
(`0x2020`, `.data` at `0x400020`). They are research leads, not a usable stock
linker script. A printable-string scan of the verified raw firmware found no
GCC/Keil/ARM compiler-version banner; absence of a string proves no compiler.

## Candidate ranking and remaining questions

1. ARMCC/ARM Compiler 5 is the strongest historical candidate because the
   public related boot map names 5.05 build 41 and the SDK includes ARM-ADS
   projects. Exact use in SlimBlade is unproven, including whether runtime
   libraries and application code used the same release.
2. GNU Arm Embedded GCC remains plausible because the related application
   project explicitly supports it. GCC version, LTO participation and library
   provenance are unestablished.
3. Clang/LLD 23.1.1 is available locally and works for synthetic ARMv5TE Thumb
   tests. No evidence identifies it as Kensington's original compiler.

Observed ARM/Thumb transitions and little-endian literals support that machine
model. They do not distinguish AAPCS from APCS variants, aggregate-return
rules, enum width, plain-char signedness, structure packing, float ABI, stack
alignment, register preservation at all interfaces, interrupt conventions or
optimization settings. Ghidra's `default` compiler spec resolves none of these.

The [official Arm compiler download index](https://support.arm.com/documentation/ka005198/1-0/?lang=en)
is a legitimate place to investigate legacy releases, but the raw download in
this session was a JavaScript application shell. The
[Keil legacy-download URL](https://www.keil.com/download/legacy/) returned HTTP
500. No exact 5.05 build-41 installer, hash, usable license or entitlement was
established. Do not obtain a repackaged proprietary compiler from an unofficial
mirror. A package-manager install of a modern compiler would not answer this
historical question.

The installed synthetic tools are CachyOS packages: `clang 23.1.1-2`,
`lld 23.1.1-1.1`, `llvm-libs 23.1.1-3`. `pacman -Qi` reports package signature
validation. The verifier records executable and dependency hashes, versions,
flags and ABI in [its lock](../bootstrap-verifier/synthetic-lock.json). These
tools were already installed, so there is no new compiler-archive retrieval
claim. Clang's [official cross-compilation documentation](https://clang.llvm.org/docs/CrossCompilation.html)
describes explicit target selection; synthetic use does not imply stock compatibility.

## Reproduction and later calibration proposal

```sh
python3 decomp/results/bootstrap-toolchain/collect.py --repo . --output .decomp/research/compiler-v1
```

Use a fresh output directory on rerun. The script reads Git history and downloads
public evidence only. It records failed fetches without treating them as sources.

A later, separately authorized calibration should first build small synthetic
ABI probes with legitimately available ARMCC 5.05 and candidate GCC releases:
signed-byte loads, 64-bit arithmetic, struct returns, switch tables and ARM/Thumb
calls. Record exact compile commands, ELF attributes, library member identities
and linked bytes. Compare fingerprints against several independently reviewed
stock regions before selecting a candidate. Fix the selected toolchain and
boundaries before any bounded function campaign. No stock C reconstruction or
compiler-guessing compile/diff attempts were performed in this bootstrap.
