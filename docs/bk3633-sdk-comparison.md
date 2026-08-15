# BK3633 SDK comparison

Last checked: 2026-08-15

## Initial result

The BK3635 SlimBlade startup is recognizably the same design as the public
BK3633 SDK startup. This is strong evidence that the SDK can supply source-level
structure for a BK3635 port, but it is not a drop-in hardware definition.

| Phase | SlimBlade v4.49 | BK3633 SDK | Result |
| --- | --- | --- | --- |
| Vectors | ARM `ldr pc` table at `0x2020`; reset target `0x2064` | ARM exception-vector table | Same structure |
| Registers | Clears `r0` through `r12` | Clears `r0` through `r12` | Exact operation; order differs |
| Stacks | Selects IRQ, FIQ, SYS and SVC modes and loads separate stack pointers | Initializes banked ARM-mode stacks | Same mechanism; sizes and modes differ |
| RAM data | Copies `0x6f4` bytes from `0x1ed60` to `0x400020` | `_data_init` copies flash `.data` to RAM | Same loop semantics |
| Zero data | Clears `0x3940` bytes from `0x400714` | `_zi_init` clears `.bss` | Same loop semantics |
| Application | Loads odd entry address `0x19879`, entering Thumb code | Branches from ARM startup into compiled application code | Same ARM/Thumb boundary |

The Kensington implementation is smaller. It omits the SDK's ABT and UND
stack initialization, writes `0xdeadbeef` guard words instead of filling whole
stack regions, clears registers before rather than after RAM initialization,
and clears `.bss` before copying `.data`. These are implementation choices, not
a different startup model.

## Application initialization pass

The Thumb entry at `0x19878` is a multi-mode initializer and main loop. These
callees can already be classified without assigning names to the remaining
application code:

| SlimBlade address | BK3633 SDK analogue | Confidence | Result |
| --- | --- | --- | --- |
| `0x17990` | watchdog disable | High | Same BK3633 register-list WDT address and key fields; the separate SDK WDT driver is stale |
| `0x17f54` | `usb_init()` device path | High | Same USB base, offsets, interrupt masks and device constants |
| `0x178ce` / `0x178ea` | nested busy-wait delay | Medium | Same purpose and loop form, but BK3635 loop counts, widths and optional watchdog feed differ |
| `0x186b8` | reset-state/reason handling | Low | Reads and clears reset state and returns one of three modes, but constants and layout do not match closely enough to port |

The USB match is particularly specific. Both implementations operate on base
`0x00804000`, enable RX and TX endpoint masks `0x07`, set USB interrupt enable
to `0x3f`, clear VTH bit 7 at offset `0x88`, use device configuration `0xf4`,
acknowledge the interrupt byte at offset `0x94`, and set the line-driver value
at offset `0x8c` to `0x77`. Kensington's final OTG configuration is `0x09`, the
same device-mode result as the SDK's `0x08` followed by OR `0x01`. Kensington
also enables `POWER` bit 0, an operation present but commented out in the SDK.

This is stronger than a shared peripheral map: the stock routine is an evolved
device-only implementation of the SDK routine. USB initialization source can
therefore be used as a porting reference after substituting verified BK3635
system-control definitions.

The SDK also includes a compiled BK3633 USB boot image and linker map. The map
identifies `usb_init` at `0x54b8`; disassembly shows the same zeroing of USB
interrupt masks, VTH-bit clear, host/device branch, device constants, interrupt
acknowledgement, `0x77` line-driver write, software-stack initialization and
final USB-reset bit. Kensington removes the host branch, changes surrounding
system setup, and inlines or replaces some helpers, but retains the distinctive
device sequence.

## USB command path

The BK3633 boot project contains a complete, working command transport rather
than only peripheral definitions:

1. `usb_init(1)` configures the shared controller block and calls
   `usb_sw_init()`.
2. The generic MicroSW stack registers `MGC_McpFunctionClient`.
3. Its configuration callback binds a 64-byte interrupt IN pipe and a 64-byte
   interrupt OUT pipe, installs completion callbacks, and starts the OUT
   transfer.
4. `USB_InterruptHandler()` snapshots `INTRUSB`, `INTRTX` and `INTRRX`, then
   passes them through `MGC_AfsUdsIsr()`.
5. The OUT completion callback sets `b_isDataing`; `bim_main()` parses the
   buffer and rearms reception.
6. Command `SET_RESET_CMD` (`0x0e`) with argument `0xa5` starts the watchdog and
   waits for reset.

The compiled reference confirms the source-level path. The 23,348-byte boot
image places `MGC_AfsUdsIsr` at `0x04c0`, the endpoint configuration callback
at `0x2838`, RX callback at `0x3860`, transmit wrapper at `0x3894`, hardware
interrupt wrapper at `0x38e4`, parser at `0x481c`, `usb_init` at `0x54b8`, and
`usb_sw_init` at `0x55dc`.

The SlimBlade transport is related but not identical. The BK3633 example's HID
configuration has interrupt IN endpoint `0x81` and interrupt OUT endpoint
`0x02`, both 64 bytes. The live SlimBlade configuration instead has mouse IN
endpoint `0x81` (7 bytes) and updater IN endpoint `0x82` (17 bytes), with no
interrupt OUT endpoint. Its 170-byte updater report descriptor declares report
ID `0x08` with 16 input and 16 output data bytes. Host output therefore arrives
as the 17-byte HID control transfer:

`21 09 08 02 01 00 11 00`

This is `SET_REPORT(Output, id=8)` to interface 1, followed by the report data.
The stock binary corroborates that path:

| Address | Observed role |
| --- | --- |
| `0x60e0` | FIQ dispatcher; tests the USB pending bit and calls `0x16dd8` |
| `0x16dd8` | Saves the endpoint index, reads USB/TX/RX interrupt state from `0x00804000`, services endpoints, then restores the index |
| `0x165a8` / `0x172cc` | Class-request dispatch and `SET_REPORT` data-stage setup |
| `0x16ef6` | Requires a 17-byte interface-1/report-ID-8 payload before calling `0x11700` |
| `0x11700` | Copies exactly 17 bytes into the vendor command buffer and marks it pending |
| `0x18f4c` | Validates and dispatches the pending vendor report |
| `0x18fba` | Command `0x0d` calls the proven loader-entry routine at `0x1895c` |

Kensington's stack is a compact register-level implementation rather than the
BK3633 boot project's generic MicroSW object graph. The BK3633 endpoint-2 OUT
loop should therefore not be ported directly. Its controller initialization,
FIFO semantics, completion model and watchdog-reset behavior remain useful
source-level evidence; the SlimBlade endpoint-0 state machine is the closer
model for custom firmware.

## Minimal recovery-trigger design

Verified constraints:

- the live-tested marker prefix runs before experimental code;
- marker persistence makes a later watchdog reset enter the resident loader;
- the exact application request is a checksummed 17-byte report beginning
  `08 0d` and ending `40`;
- the Rust protocol crate now accepts only the exact setup packet and exact
  valid reset report as a recovery request.
- `slimblade-usb` now parses setup packets without host-endian assumptions,
  classifies the minimal standard/HID request set, and models recovery as
  setup, OUT-data and status-completion stages.

The pure Rust recovery model returns `EnterLoader` only after status
completion. A new setup packet, malformed report, unrelated valid command or
bus reset cancels the pending action. Host tests cover these cases and complete
descriptor packetization. The crate has no MMIO and is not linked into the
live-tested guard yet.

`slimblade-bk3635` now adds the hardware boundary. Its typed register set can
represent only stock-observed USB platform, clock, interrupt-control, and
controller addresses, while the sole live backend contains four reviewed
volatile operations behind an unsafe constructor. A fake backend verifies the
complete Kensington device-mode initialization order, clear-on-read interrupt
snapshot, descriptor CSR/FIFO order, the full synthetic
enumeration/address/configuration path, and status-gated loader result. The
OUT-status boundary now matches Kensington helper `0x170e8`: CSR0-high `0x01`
then CSR0-low `0x0a`.

The smallest first implementation should keep the audited marker prefix,
initialize only USB device mode, enumerate the existing two-interface
descriptor shape, service endpoint 0, acknowledge the complete `SET_REPORT`
transaction, and then use the proven watchdog reset. Experimental USB code
must not access the nonvolatile controller or marker storage after the prefix.

The separate `bk3635-usb-probe` package links that path after the exact
live-tested 420-byte marker prefix. Its first candidate ran on hardware on
2026-08-15. All 3,748 loader blocks echoed with the
expected CRC, but the probe did not enumerate. Removing USB power for five
seconds returned the same port to resident loader `25a7:fabe`, whose query
returned `d2`; the marker-first recovery path therefore worked as designed.

Comparison against Kensington's byte-identical v4.48/v4.49 initializer exposed
that the first probe followed the related BK3633 SDK sequence, not the exact
BK3635 sequence. It asserted a non-stock USB reset bit and omitted the
Kensington platform, clock, `DEVCTL`, POWER, and related activation writes. The
corrected candidate reproduces the complete Kensington operation transcript.
Its host-only audit passes at 3,632 bytes (3,212 experimental), SHA-256
`cbe5bbbb119885f9d5b861b5548371a80672ada9b0ad9014069f12c8e41a9eca`.
It has 14 decoded allowlisted MMIO loads, no undefined/runtime symbols, and a
184-byte maximum stack frame. Its hash-locked 128,112-byte container SHA-256 is
`3ce23e3b9af4a1e713bad622f56fc9055cb178ca1ec198c7556c1dee44169e5a`.
The corrected candidate also failed to enumerate on hardware after all 3,748
blocks echoed. Its marker recovered loader `25a7:fabe`/`d2` after a USB power
cycle, and exact v4.53 restoration passed. This shows that exact controller
register replay is insufficient without some earlier stock initialization or
the stock FIQ service path.

Inference: a tight polling loop can replace FIQ dispatch for a first probe,
avoiding new interrupt-controller and FIQ-state dependencies. The endpoint
registers latch requests until serviced, but polling latency is still the main
unverified hardware assumption.

Open before the next probe candidate:

- retain complete stock startup and USB initially, set the recovery marker
  before stock startup, and add custom code only behind a reviewed hook;
- first observe enumeration without sending command `0x0d`, then test that
  command only as a separate explicit stage;
- rerun the complete gate and review the new exact hash immediately before any
  explicit hardware request.

Hardware result on 2026-08-15: the exact hash-locked container passed `B2/d2`
and all 3,748 loader echoes, but did not enumerate as `047d:80d7`/`0454` after
the loader exited. No `0x0d` command was sent. This falsifies the first polling
probe as a working USB application; it does not yet distinguish initialization
failure from endpoint-zero polling failure. The subsequent power-cycle recovery
and exact v4.53 restoration both succeeded.

Source for the CSR comparison: vendored [Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk)
commit `0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14. The
initial 1,091-file SDK import is 13,718,399 bytes with deterministic tree
SHA-256 `2df03cb56bab839de7a51b8aefdc5fc0f481e405ddc12be18ee33f4bdfffe3c6`.

## Hardware-definition evidence

- Both use the ARM968E-S/ARMv5TE instruction contract inferred for BK3635.
- The SDK register list places the watchdog at `0x00806000` and defines its key
  in bits 16–23. Kensington uses that same address and writes keys `0x5a` and
  `0xa5` in those bits.
- The SDK WDT driver instead targets an older always-on watchdog at
  `0x00800c00`. That source file is not compatible with the stock BK3635 WDT
  routine even though the generated register list contains the correct block.
- The SDK also labels `0x00803000` as general DMA, while Kensington uses that
  region as its nonvolatile-memory controller. Peripheral names and layouts
  therefore cannot be copied without checking the BK3635 binary.
- SDK stack tops near `0x00410000` are invalid for the BK3635's documented
  32 KiB RAM. Kensington's highest observed stack pointer is below
  `0x00408000`.

## Interpretation

Verified: the SDK provides usable source for the vector table, CPU-mode setup,
runtime RAM initialization, interrupt wrappers, linker concepts and much of the
application framework.

The first BK3635-specific SDK project is now under
[`SDK/projects/slimblade_wired`](../vendor/bk3633_sdk/SDK/projects/slimblade_wired/README.md).
Its readable ARM assembly rebuilds stock v4.49 `0x2020`--`0x21ab` exactly: 396
bytes, SHA-256
`60d7616f48e2e457787e28748aec0b8afd404af35094cc8ef6b74c660c9248d8`.
The hash-locked Rust SDK-startup verifier checks the stock input, every
generated byte, ELF address/size/entry point, vector
targets, reset call targets, ARM-to-Thumb entry and absence of relocations or
writable allocated data. This establishes source control over reset, mode/stack
setup, `.data` copy and `.bss` clearing without claiming equivalence for later
peripheral initialization.

The same project also rebuilds the IRQ/FIQ span `0x2300`--`0x232f` exactly: 32
instruction bytes around the stock 16-byte zero gap, SHA-256
`02e811fe3f434dd0fc697621bfbdc9cd74eee2d1e5d16df93f94f15fe7e5df9d`.
The verifier decodes its Thumb dispatcher targets as IRQ `0x3e78` and FIQ
`0x60e0`. These wrappers are retained for a later interrupt-driven firmware;
the recovery-only stub deliberately disables IRQ/FIQ and does not use them.

Inference: some BK3635 peripheral drivers will be close enough to port by
changing register definitions, particularly where Kensington instruction
sequences and SDK macros agree.

Open: identify the remaining clock, GPIO, interrupt, flash and sensor calls in
the Thumb entry. Instruction matching must normalize linked addresses and
compiler register allocation; byte-for-byte equality is not expected for
compiled C. A routine is only reusable when its MMIO behavior also agrees.

`cargo xtask disassemble-stock FIRMWARE START STOP arm` (or `thumb`) validates
the external file against the recorded v4.49 identity before invoking LLVM's
ARM disassembler. The firmware remains outside the repository.

## Source record

The build-relevant SDK source is now vendored under
[`vendor/bk3633_sdk`](../vendor/bk3633_sdk/README.md). Source:
[Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk), commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14. Compiled
reference artifacts were inspected in temporary storage and are not committed.

The connected v4.53 device was also read through Linux sysfs on 2026-08-15.
Its mouse report descriptor is 87 bytes with SHA-256
`57ba4a24f985a806132a04fea06bec3026cb69b12c957a1737a64507148fa968`;
its updater report descriptor is 170 bytes with SHA-256
`a8bc6d8de4d8c0674e7db3e2d238a260602fc9499a634e4d1bbd418091bfc5c6`.
The combined 18-byte device and 59-byte configuration descriptor stream is 77
bytes with SHA-256
`91918d3d08ae4958080a78fe2c7d83ff58204ae4fc61fb48c01799d9483653ff`.
The 59-byte configuration descriptor at v4.49 file offset `0x1e7e3` has
SHA-256
`4f2b4eb1bd9f89cfbc070c34ecaa391a32fb0505933783c9e8653c30543e9e20`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `SDK/src/system/startup_boot.S` | 6,053 | `c52aa16232d9162f7cae4e89010d4e9d1f92e9a81be45fde0ed66e23904af054` |
| `SDK/src/system/boot_vectors.s` | 3,426 | `08a58ea61dc6f1227c7008960115d36e27eaa9dc109b1a34743cc0fdc709a109` |
| `SDK/src/header/BK3633_RegList.h` | 467,689 | `c98f9494074b52feb19821e2be9e951a6eb684ef784c9ecf07fe19f0646f39b0` |
| `SDK/src/driver/icu/icu.c` | 11,733 | `5e31af6936ba0149eb2bac8a3d3b1b49fd7376a112624f145575c75b9236e822` |
| `SDK/src/driver/usb/driver_usb.c` | 2,679 | `7ad43f106355b4ac9a3d6c7e1bced67688490e51a919de3a8ab01a8ddb75dc03` |
| `SDK/src/driver/usb/driver_usb.h` | 6,292 | `d66a8396294019c9b2b9f4a16da2380d35cf5a9941d6f9f04aedea9b11a1ee95` |
| `SDK/src/driver/wdt/wdt.c` | 608 | `a7c9d3d2a0a14d16bca7cbb8671e1d44e226c566096fc313aa35bf64359a175d` |
| `SDK/src/driver/wdt/wdt.h` | 681 | `bdc5d1e29fa817409f6c70cc49ab33fb1ab6ab747d02cc9448ee659c2c479b31` |
| `SDK/projects/app_mouse/app/src/main.c` | 11,676 | `2e5543ca8cc4425601449b2e38d7c651081b158d6fa94f364966840642929f27` |
| `SDK/projects/app_2.4g/boot_usb/usb/driver_usb.c` | 2,537 | `b6a90f7c45a5defdb6a8992e51ff7bfa887a847149fb4e2705cb6d474cb0b5fd` |
| `SDK/projects/app_2.4g/boot_usb/app/bim_app.c` | 15,036 | `c3c97da7b59d5ababf7ecb7ec773197c43d6dc092cfcf4aae6ff7174d397e735` |
| `SDK/projects/app_2.4g/boot_usb/usb/src/examples/msd/mu_msdfn.c` | 11,455 | `ff96b3540c18d40d2ed20db2aaaef7590be59897b4b757b425cd8058215001e4` |
| `SDK/projects/app_2.4g/boot_usb/lst/bk3633_boot.map` | 29,259 | `126722c2df4c6e6385839513e4f27c4e81743b7304ba8ac75fc6266413936985` |
| `SDK/projects/app_2.4g/boot_usb/output/bk3633_boot.bin` | 23,348 | `28e364d2328cf8732290bb063b17a57bc57fabddf7c924322b602e5d1b73fe53` |
