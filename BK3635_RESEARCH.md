# BK3635 development research

Last checked: 2026-08-16

## Bottom line

- No publicly indexed BK3635-specific C SDK, register header, SVD,
  reference manual, linker script, Keil device pack, or debug configuration
  was found.
- The strongest supported CPU identification is **ARM968E-S / ARMv5TE**,
  little-endian, with ARM/Thumb interworking. Beken's public page only calls
  it a "32-bit RISC MCU", so the exact core name remains a very
  high-confidence inference from the related SDK and Kensington binary rather
  than an explicit BK3635 vendor statement.
- The public BK3633 SDK is the best available source base, but it is not a
  drop-in BK3635 hardware description.
- Compilation is already solved in this repository for both C/assembly and
  Rust. The missing pieces are primarily the complete BK3635 peripheral map
  and its JTAG/SPI entry and programming contract.
- JTAG debugging is plausible, but ordinary JTAG access and flash programming
  are separate problems. A generic probe might halt the ARM core and inspect
  memory while still lacking the BK3635 embedded-flash algorithm.
- Beken appears to distribute newer SDKs through project-approved private
  GitLab access. A genuine company evaluation inquiry has a realistic chance
  of obtaining the missing DesignKit under NDA.

## What exists publicly

### Exact BK3635 material

Beken's [BK3635 product page](https://www.bekencorp.com/en/goods/detail/cid/46.html)
provides only a product-level specification:

| Property | Published value |
| --- | --- |
| Core | "32-bit RISC MCU", up to 16 MHz |
| Flash | 160 KiB embedded, with read-out protection |
| RAM | 32 KiB |
| Debug/programming | JTAG debugging and SPI flash download |
| Radio | Bluetooth 5.2 BR/LE and proprietary 2.4 GHz |
| USB | USB 2.0/1.1 full-speed |
| Packages | QFN56 7 x 7 mm and QFN32 4 x 4 mm |
| Peripherals | SPI, two UARTs, I2C, PWM, I2S/PCM, ADC, timers, watchdog, TRNG, AES-128 |

Exact searches across Beken, GitHub, Gitee, Sourcegraph, and general web
indexes returned no meaningful results for:

- `BK3635_RegList.h`
- `CFG_CPU_BK3635`
- `bk3635_ble_sdk`
- `BK3635_DesignKit`
- BK3635 SVD files
- BK3635 Keil projects
- BK3635 OpenOCD configurations

This does not prove an SDK was never posted somewhere obscure, but there is no
presently discoverable public package.

### Public BK3633 SDK

Beken has an official
[BK3633 BLE SDK on Gitee](https://gitee.com/beken-corp/bk3633_ble_sdk). This
repository contains a carefully vendored copy at commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`.

The local import has:

- 1,091 build-relevant files;
- 688 headers;
- 339 C files;
- assembly startup and interrupt wrappers;
- GCC Makefiles;
- Keil uVision projects;
- linker configurations;
- USB host/device code;
- BLE, proprietary 2.4 GHz, mouse, and boot projects;
- peripheral drivers;
- a large generated register header;
- Apache-2.0 licensing;
- no SVD files.

Useful local entry points:

- [SDK provenance](vendor/bk3633_sdk/UPSTREAM.md)
- [BK3633 register definitions](vendor/bk3633_sdk/SDK/src/header/BK3633_RegList.h)
- [BK3633/BK3635 comparison](docs/bk3633-sdk-comparison.md)
- [BK3635-specific startup project](vendor/bk3633_sdk/SDK/projects/slimblade_wired/README.md)

The SDK is valuable for:

- ARM startup structure;
- CPU-mode and banked-stack initialization;
- ARM/Thumb transitions;
- IRQ/FIQ wrappers;
- USB controller architecture and FIFO behavior;
- linker concepts;
- GPIO, UART, SPI, timer, and other driver patterns;
- examples of Keil and GCC configuration.

It is unsafe to copy its register map wholesale. Confirmed incompatibilities
include:

- BK3633 calls `0x00803000` general DMA; BK3635 uses it as its nonvolatile
  storage controller.
- BK3633 calls `0x00806500` TIMER0; BK3635 USB initialization uses registers
  at `0x00806520` and `0x00806524`.
- The SDK contains two conflicting watchdog implementations; only the
  generated `0x00806000` definition agrees with BK3635.
- BK3633 linker layouts assuming RAM near `0x00410000` exceed BK3635's 32 KiB
  RAM.
- BK3633 itself is publicly described with much more flash/RAM and a higher
  clock despite sharing the underlying software design.

## Architecture

The best-supported BK3635 target is:

```text
ARM968E-S
ARMv5TE
32-bit little-endian
A32 ARM + Thumb-1
soft-float EABI
ARM/Thumb interworking
```

The official
[ARM968E-S Technical Reference Manual](https://documentation-service.arm.com/static/5e8e2d19fd977155116a71be?token=)
confirms that this core:

- belongs to the ARM9 Thumb family;
- implements ARMv5TE;
- executes 32-bit ARM and 16-bit Thumb instructions;
- uses classic ARM exception modes and banked registers;
- provides IEEE 1149.1 JTAG debug;
- uses EmbeddedICE-RT;
- has two hardware watchpoint units;
- provides a CP14 debug communications channel;
- may be synthesized with full or reduced debug support.

Important consequences:

- It is not Cortex-M.
- It does not use NVIC.
- It is not an SWD target.
- Thumb means original Thumb-1, not Thumb-2.
- Exception vectors enter ARM state.
- Startup requires separate SVC/IRQ/FIQ stacks.
- Code pointers use bit 0 to select Thumb state.
- Floating point needs software routines.
- Modern Cortex-M crates, startup code, and probe assumptions generally do
  not apply.

The Kensington binary confirms this execution model: ARM vectors and startup
at `0x2020`, followed by an odd-address transition into Thumb application
code.

### Established memory map

| Range/address | Meaning | Confidence |
| --- | --- | --- |
| `0x00000000-0x00027fff` | 160 KiB flash address space | High |
| `0x00000000-0x00001fff` | Resident USB loader region | High |
| `0x00002000` | Application update boundary | Live-proven |
| `0x00002010` | Application metadata | High |
| `0x00002020` | Application ARM vectors/startup | Exact binary match |
| `0x00400000-0x00407fff` | 32 KiB RAM | High |
| `0x00800000` | System-control block | High |
| `0x00803000` | BK3635 nonvolatile-storage controller | Live-proven subset |
| `0x00804000` | USB controller | High |
| `0x00806000` | Watchdog | Live-proven |
| `0x00806520/24` | USB-related platform controls | Stock-observed |

The existing typed BK3635 register subset is in
[`crates/slimblade-bk3635/src/lib.rs`](crates/slimblade-bk3635/src/lib.rs).
That subset is currently more trustworthy than an automatic conversion of the
entire BK3633 header.

## Development tools

### C and assembly

Both GCC and LLVM are suitable. The BK3633 Makefiles use:

```text
-mcpu=arm968e-s
-march=armv5te
-mthumb
-mthumb-interwork
```

The BK3635 startup reconstruction uses Clang/LLD with the same CPU and
architecture and reproduces the Kensington startup bytes exactly:

- [BK3635 startup Makefile](vendor/bk3633_sdk/SDK/projects/slimblade_wired/Makefile)
- [BK3635 recovery-stub linker layout](firmware/recovery_stub/recovery_stub.ld)

Suitable tools include:

- `arm-none-eabi-gcc`;
- `arm-none-eabi-binutils`;
- Clang, LLD, LLVM objcopy, and LLVM objdump;
- GDB configured for ARM;
- Ghidra using little-endian ARMv5;
- IDA's ARM processor module.

### Rust

Rust officially provides `armv5te-none-eabi` and `thumbv5te-none-eabi`. They
are Tier 3 bare-metal targets supporting `core` and `alloc`; the Thumb target
emits Thumb-1 by default and supports interworking. See the
[Rust target documentation](https://doc.rust-lang.org/rustc/platform-support/armv5te-none-eabi.html).

This repository already builds `core` from source for
`thumbv5te-none-eabi`:

- [Rust target configuration](firmware/bk3635-rs/.cargo/config.toml)
- [Pinned toolchain](firmware/bk3635-rs/rust-toolchain.toml)
- [Rust firmware notes](firmware/bk3635-rs/README.md)

Rust code generation is no longer speculative: Rust functions and a custom
Rust USB-report runtime have executed on this BK3635.

### Keil

The BK3633 projects identify the target as:

```text
ARM9E-S (Little Endian)
CPUTYPE(ARM9E)
```

The JTAG-specific project selects SEGGER's `JLTAgdi.dll`. Current
[Keil MDK documentation](https://developer.arm.com/Tools%20and%20Software/Keil%20MDK)
says Arm7/Arm9 legacy cores remain supported through uVision rather than the
modern Cortex-oriented workflow.

### JTAG software and probes

The clearest supported commercial route is Keil/ULINK. Keil explicitly
recognizes `ARM968` as an ARM968E-S chain identifier, and ULINK supports Arm9
JTAG. See the
[ULINK JTAG chain documentation](https://www.keil.com/support/man/docs/ulinkpro/ulinkpro_su_dev_chain.asp).

J-Link is also plausible because:

- the BK3633 JTAG project selects the J-Link Keil driver;
- SEGGER supports other ARM968E-S devices;
- the ARM core's EmbeddedICE debug mechanism is standard.

However, BK3635 itself is not in SEGGER's public device list. Expect generic
core debugging at best unless Beken supplies a device script and flash loader.

OpenOCD supports `arm966e`, but does not list a distinct ARM968E-S target. The
ARM966E-S and ARM968E-S debug models are closely related, so `arm966e` is a
reasonable experiment after a TAP is visible, not a proven BK3635
configuration. See the
[OpenOCD CPU configuration](https://openocd.org/doc-release/html/CPU-Configuration.html).

A successful JTAG connection does not imply flash-writing support. Core halt,
registers, breakpoints, and RAM access use EmbeddedICE. Programming the
embedded flash needs Beken's controller algorithm or factory SPI protocol.

## Rear-pad interpretation

The SlimBlade board has:

```text
RSTN P04 P05 P06 P07 VCC GND
```

The related BK3633 datasheet maps:

| Pad | JTAG mode | Factory programming mode |
| --- | --- | --- |
| `P04` | TDI | SPI MOSI |
| `P05` | TDO | SPI MISO |
| `P06` | TCK | SPI SCK |
| `P07` | TMS | SPI CS |
| `P03` | nTRST | -- |

This is strong evidence that the photographed cluster is a combined JTAG/SPI
production connector. It remains an inference until the BK3635 TAP responds.

The missing `P03/nTRST` is not necessarily fatal: the JTAG TAP itself can
normally be reset by holding TMS high for at least five TCK cycles. The unknown
part is how BK3635 chooses JTAG, programming, or normal mode at reset.

Before connecting a probe:

- Measure the pad voltage; do not assume 3.3 V.
- Use VCC as probe reference/sense unless the electrical design specifically
  calls for probe power.
- Share ground.
- Start with a low JTAG clock.
- Treat the first attempt as a read-only TAP/IDCODE scan.
- Do not attach a generic SPI-NOR programmer. The embedded flash and Beken
  programming protocol are not established as ordinary SPI NOR.

Read-out protection or a secure-debug fuse may prevent flash reads even if the
TAP responds. It might still permit halt, RAM access, or mass erase; only the
BK3635 security documentation can settle that.

The local physical evidence is summarized in
[board-observations.md](docs/board-observations.md).

## JTAG is not normally required for application development

Before the present `0475` failure, the SlimBlade's resident USB loader had
already:

- accepted modified images;
- accepted standalone custom ARM code;
- run Rust code;
- restored stock images;
- returned raw data from both optical sensors;
- carried custom unsolicited USB reports.

The normal development loop can ultimately remain:

```text
compile -> pack image -> USB loader -> execute -> report diagnostics over USB
```

JTAG is mainly needed now for recovery and, later, for breakpoints and direct
memory inspection.

The current device is in a watchdog-reset loop because `0475` replaced a
pre-marker mode-transition handler. USB still enumerates, but the application
never services the command that enters the loader, and the persistent recovery
marker was never reached. No further custom flash should occur until the
per-version marker-reachability gate passes. See
[custom-main-handoff.md](docs/custom-main-handoff.md).

## Obtaining the real SDK from Beken

This is probably the highest-yield path.

Beken publishes global contact information at
[`info@bekencorp.com`](mailto:info@bekencorp.com), with Shanghai headquarters
and Asian offices listed on its
[contact page](https://www.bekencorp.com/en/services/contact.html).

More significantly, Beken's current BK3633 documentation instructs developers
to clone an SDK from a private Beken GitLab and says that the account is
obtained through project approval. That establishes an actual vendor process.
See the
[Beken FindMy SDK instructions](https://docs.riselink.ai/arminodoc/bk_findmy/bk3633/en/v2.0.1/get-started/index.html).

A credible request should include:

- company legal name and website;
- application: low-power HID/IoT device evaluation;
- expected prototype quantity and possible annual volume;
- exact part: `BK3635UQN56A` / QFN56;
- whether Bluetooth, proprietary 2.4 GHz, and USB are required;
- desired development schedule;
- willingness to sign an NDA;
- request for a regional FAE or distributor introduction.

Ask explicitly for:

1. Latest BK3635 datasheet and QFN56 pinout.
2. BK3635 hardware design guide and reference schematic.
3. BK3635 DesignKit/SDK, including full C source where available.
4. `BK3635_RegList.h` or equivalent peripheral headers.
5. Register/reference manual and complete memory map.
6. Startup, linker, and Keil/GCC projects.
7. USB HID mouse/keyboard examples.
8. SVD, IP-XACT, or another machine-readable register description.
9. JTAG mode-entry sequence, IR length, expected IDCODE, and supported probes.
10. Secure-JTAG/readout-protection and mass-erase behavior.
11. Factory SPI programming protocol and pad mapping.
12. Supported versions of BKFIL, `bk_writer`, or an offline programmer.
13. Debugger scripts and the embedded-flash programming algorithm.
14. Errata, lifecycle status, sample availability, and evaluation boards.
15. Recovery procedure for a device whose application continuously resets.

### Suggested initial email

> **Subject: BK3635UQN56A SDK and development-tool evaluation**
>
> I am evaluating the BK3635UQN56A for a possible low-power HID/IoT product at
> [company]. The intended design requires wired USB and may also evaluate
> Bluetooth/proprietary 2.4 GHz.
>
> Please connect me with the appropriate FAE or distributor and advise on NDA
> access to the BK3635 DesignKit, complete datasheet, register documentation,
> QFN56 reference design, JTAG/debug configuration, factory SPI programming
> guide, supported programming tools, and sample or evaluation-board
> availability.
>
> Initial prototype quantity is [quantity], with potential annual volume of
> [estimate] subject to evaluation.

Other legitimate routes include:

- Asking Beken for the nearest authorized distributor or FAE.
- Contacting [RiseLink](https://www.riselink.ai/developers), Beken's current
  US-facing distribution/developer organization, and asking for routing to the
  legacy Bluetooth team.
- Obtaining the TuyaOS BK3633 development package, which reportedly includes
  `BK3633_DesignKit_V06_2411`, BKFIL, and `bk_writer`. It is useful for
  sister-chip evidence, not an exact BK3635 solution. See the
  [Tuya BK3633 platform guide](https://developer.tuya.com/cn/docs/iot-device-dev/bluetooth_platform_ble_bk3633?id=Kdi0in7x1sbwe).
- Asking chip suppliers for a manufacturer-authorized SDK and confirming
  redistribution and licensing terms before using it.
- Asking Kensington/ACCO for factory recovery assistance, although they are
  unlikely to redistribute Beken's SDK.

The most useful immediate outcome from Beken would be smaller than a complete
SDK: the BK3635 pinout, debug-mode entry sequence, security state, and factory
SPI programming guide would be enough to unblock recovery.
