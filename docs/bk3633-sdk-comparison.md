# BK3633 SDK comparison

Last checked: 2026-08-14

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
The hash-locked [`verify_sdk_startup.py`](../tools/verify_sdk_startup.py) checks
the stock input, every generated byte, ELF address/size/entry point, vector
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

[`tools/disassemble_stock.py`](../tools/disassemble_stock.py) provides
hash-locked ARM or Thumb disassembly of chosen v4.49 ranges without placing the
firmware in the repository.

## Source record

The build-relevant SDK source is now vendored under
[`vendor/bk3633_sdk`](../vendor/bk3633_sdk/README.md). Source:
[Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk), commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14. Compiled
reference artifacts were inspected in temporary storage and are not committed.

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
| `SDK/projects/app_2.4g/boot_usb/lst/bk3633_boot.map` | 29,259 | `126722c2df4c6e6385839513e4f27c4e81743b7304ba8ac75fc6266413936985` |
| `SDK/projects/app_2.4g/boot_usb/output/bk3633_boot.bin` | 23,348 | `28e364d2328cf8732290bb063b17a57bc57fabddf7c924322b602e5d1b73fe53` |
