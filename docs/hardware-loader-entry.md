# Hardware-assisted loader entry

Last checked: 2026-08-16

## Outcome

No verified passive strap has been found that makes the BK3635 enter the
SlimBlade USB loader. Do not short `P04` through `P07`: they are multiplexed
programming/debug signals and may become outputs.

The strongest hardware recovery path is the factory SPI interface on the
photographed pad cluster. The first operation must be a read-only flash dump
with a Beken-compatible HID SPI programmer. If the dump works, it provides the
missing complete resident-loader backup before any repair is attempted.

Forcing the USB loader can then be considered by making the application fail
its loader validation while preserving the first 8 KiB. Directly restoring the
locked `0474` application through the same programmer may be simpler and safer.
Neither write should be attempted until the dump, address translation, and
loader boundaries are verified.

## Verified evidence

- The board exposes `RSTN`, `P04`, `P05`, `P06`, `P07`, `VCC`, and `GND` as a
  single factory-pad cluster.
- The official BK3633 datasheet maps `P04=MOSI`, `P05=MISO`, `P06=SCK`, and
  `P07=CS` in programming mode. In JTAG mode they become TDI, TDO, TCK, and
  TMS. The assignments exactly match the SlimBlade pad labels.
- Beken's BK3633 quick-start guide says the chip supports transparent SPI flash
  programming and UART1 download. It shows a Beken HID programming board on
  P04–P07 and a tool with read, erase, and download operations. Its documented
  UART method starts the host operation first and then powers the target.
- The same guide's SPI example selects BK3435 in `HID Download Tool V2.5.5`.
  This appears to be a shared Beken programming transport; it does not prove
  that BK3435 settings are safe for BK3635.
- The related BK3633 USB loader selects loader operation from persistent flash
  state or an invalid application. Its `bim_main()` does not read a GPIO boot
  strap. This is related-chip evidence, not proof of BK3635 implementation.
- The failed `0475` hook starts in the application region and did not rewrite
  the resident loader. The device's repeated `047d:80d7` enumeration confirms
  that its application still starts and its USB hardware remains functional.

## Candidate SPI wiring

These assignments are evidence-backed but remain a BK3635 hypothesis until a
non-writing transaction succeeds:

| SlimBlade pad | Programming signal | Use |
| --- | --- | --- |
| `P04` | SPI MOSI | programmer output to target |
| `P05` | SPI MISO | target output to programmer |
| `P06` | SPI SCK | clock |
| `P07` | SPI CS | chip select |
| `RSTN` | reset | programmer-controlled reset, if supported |
| `VCC` | target voltage | reference or supply only as specified by the programmer |
| `GND` | ground | common reference |

The board must have exactly one power source. Normal USB is appropriate only if
the programmer treats `VCC` solely as a target reference. If the programmer is
designed to power its target, USB must be disconnected and its output voltage
verified first. Never inject 5 V at `VCC` or drive it from two sources. Pogo
pins are preferable only when held in a stable aligned fixture; otherwise,
fine soldered leads with strain relief are safer than loose contacts.

## Programmer choice

The preferred development adapter is a genuine FT232H breakout rather than an
old Beken production fixture. FT232H provides MPSSE SPI plus spare GPIO for
`RSTN`, works on Linux, and can be driven from Rust using
`ftdi-embedded-hal` with its open-source `libftdi` backend.

As checked on 2026-08-16, Core Electronics listed the Adafruit FT232H breakout
(`ADA2264`) in stock for AUD 27.80. Adafruit listed the same board for USD 14.95.
An eBay FT232H breakout may be equivalent, but the listing must show an actual
FT232H, 3.3 V logic, accessible MPSSE pins `D0` through `D3`, and additional
GPIO. FT232RL/FT231X UART adapters, CH341A desktop flash programmers, ST-Link,
and SWD-only CMSIS-DAP probes do not provide the required interface.

No connection is safe until the live SlimBlade `VCC` pad voltage is measured.
FT232H logic is 3.3 V; a lower target voltage would require proper level
translation. The initial adapter program will expose only reset, mode-entry,
JEDEC identification, and bounded reads. Erase and write operations will not
be implemented until two matching dumps pass offline verification.

### Hardware shopping list

The focused list below is supplemented by the reusable
[embedded development workbench](embedded-workbench.md).

- One genuine Adafruit FT232H breakout (`ADA2264`). It includes unsoldered male
  headers. The Australian Core Electronics listing is preferable to an unknown
  eBay clone while it remains available at a similar price.
- One USB-C data cable for the breakout, with a connector at the host end that
  matches the development computer. It must carry data, not charge only.
- One 10 or 20 cm female-to-female 2.54 mm jumper ribbon. Six leads can have one
  connector cut off and be soldered directly to `P04` through `P07`, `RSTN`,
  and `GND`; their remaining female ends fit the FT232H headers.
- A digital multimeter with DC-voltage and audible-continuity modes. It is
  required for measuring `VCC`, finding shorts, and checking every connection
  before the adapter is plugged in.
- Fine electronics solder (approximately 0.5--0.7 mm), a no-clean flux pen,
  fine tweezers, and polyimide tape. The tape must provide strain relief so the
  jumper cable cannot lift a SlimBlade test pad.
- A stable PCB holder or helping-hands tool and adequate magnification. These
  are strongly recommended because the pad cluster is small and six adjacent
  wires must remain isolated.
- Desoldering braid for correcting a bridged joint, plus eye protection and
  suitable solder-fume ventilation.

Pogo contacts remain an alternative only if mounted in a stable, aligned
fixture. Six loose hand-held probes are not reliable enough for a flash dump.
`VCC` initially needs only a multimeter probe; it must not be connected as a
power feed.

For an eBay purchase, search for `FT232H breakout MPSSE SPI GPIO`. The listing
must name FT232H explicitly and expose `D0` through `D4`; a board advertised
only as an FTDI serial/UART adapter is not suitable. No separate Beken
programmer is needed for the planned read-only experiment because the host-side
Rust tool will generate the candidate entry sequence directly.

Do not buy a level shifter, bench supply, logic analyser, or dedicated Beken
programmer yet. A level shifter becomes necessary only if the measured target
logic voltage is incompatible with the FT232H's 3.3 V signalling.

### Captured protocol lead

An independent GPL-3.0 ESP32 project captured the factory SPI protocol for
BK3431Q/BK3432. Its source enters transparent programming with repeated `D2`
commands at 500 kHz, then uses flash-style identification and access commands.
The code has no reliable readback verification and includes whole-chip erase,
so it must not be run on the SlimBlade. It is useful only as protocol evidence
for a new read-only implementation.

The project's `bkdownload.rar` attachment was retrieved on 2026-08-16:
4,344 bytes, MD5 `d6aada3a4a8bc1fd21eef7990ee03f4c`, SHA-256
`22c881ef23bd3f41db87eb622bd020c0116a39e088285d7996ccea7b366a83d7`.
It contains 23,273 uncompressed bytes across three Arduino/C++ source files.

## Staged hardware gate

Stop at the first failure or ambiguous result:

1. Identify a Beken-compatible HID SPI programmer and its exact voltage and
   reset behavior. A generic desktop SPI-flash programmer is not equivalent.
2. With the board unpowered, check that no proposed signal is shorted to ground
   or supply.
3. Connect only the programming signals, ground, target reference, and reset.
4. Request chip identification or a small read. Do not erase, unlock, program,
   or write eFuse/configuration data.
5. If reads work, dump the complete addressable flash at least twice. Require
   identical hashes and compare the known `0475` application bytes.
6. Determine the programmer's physical-to-CPU address translation and archive
   the exact resident-loader bytes and full dump identity.
7. Build and independently verify one minimal recovery action:
   either invalidate only the application metadata so the resident loader is
   selected, or restore the exact locked `0474` application region.
8. After any write, verify the programmed bytes before reset. Then observe for
   known loader VID/PIDs and issue the existing non-writing loader query.

Steps 1–6 do not intentionally modify the target. No whole-chip erase is
acceptable. No eFuse operation is acceptable: Beken documents eFuse changes as
irreversible and notes that its low region can disable JTAG and flash download.

## Why JTAG is not the primary recovery path

Beken's BK3633 JTAG guide uses a J-Link at 500 kHz and a hardware-reset strategy,
but explicitly requires a runnable image that does not close JTAG. The SDK's
`CFG_JTAG_DEBUG` build preserves JTAG; ordinary firmware and the USB loader
clear system-register bit 9 during early ICU initialization.

The current `0475` image still contains the live-tested Thumb `marker_set`
routine at `0x000021d8`. Calling it through a debugger would be elegant, but
the official guide indicates that attaching after firmware has disabled JTAG
will fail. A reset-time mode-selection mechanism could change that conclusion,
but no BK3635-specific sequence has been found. JTAG is therefore a secondary
experiment after SPI recovery, not the basis of the recovery plan.

## UART alternative

The BK3633's programming-mode table maps UART download to `P00/P01`, which are
also USB D-/D+ in normal mode. Its official `bk_writer` procedure starts a
1,000,000-baud UART operation before target power-on. This suggests a ROM-level
serial fallback that is independent of the application, possibly reachable
through a USB breakout cable and a 3.3 V UART adapter.

BK3635 UART download support has not been verified, and the normal PC USB host
cannot perform this electrical UART protocol. SPI uses the pads that are
already exposed and has stronger physical evidence on the SlimBlade board.

## Unresolved items

- BK3635-specific programming documentation and the exact startup
  mode-selection command have not been found publicly.
- The correct modern Beken HID programmer hardware/software combination for
  BK3635 is not yet identified.
- Readout protection may prevent flash reads. The BK3635 product page advertises
  readout protection but does not state whether Kensington enabled it.
- SlimBlade resident-loader behavior with deliberately invalid application
  metadata has not been tested. Related BK3633 source enters its USB loader in
  that condition.
- The exact minimal physical flash range for restoring `0474` must be derived
  from a successful dump; the updater container must not be written directly
  as though it were a raw flash image.

## Sources

- [Beken BK3635 product page](https://www.bekencorp.com/en/goods/detail/cid/46.html),
  retrieved 2026-08-16: JTAG debugging, SPI flash download, 160 KiB embedded
  flash, and readout protection.
- [Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk), commit
  `0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14.
- [BK3633 Datasheet V0.5](https://gitee.com/beken-corp/bk3633_ble_sdk/raw/master/BK3633%20Datasheet_V0.5.pdf),
  retrieved 2026-08-16: 600,626 bytes, SHA-256
  `2772e7ca7f9c253c478d9c8547100fce34cc99db0f86e8fd48f920fded9a4da5`.
- [BK3633 quick-start guide V1.0](https://gitee.com/beken-corp/bk3633_ble_sdk/raw/master/Tools/BK3633%E4%BD%BF%E7%94%A8%E5%BF%AB%E9%80%9F%E5%85%A5%E9%97%A8.pdf),
  retrieved 2026-08-16: 828,711 bytes, SHA-256
  `347e019c5701dbc6b8e9b2b2249efc346dc3dad42a29bea0b7dbaa26024736cb`.
- [BK3633 JTAG debugging guide](https://gitee.com/beken-corp/bk3633_ble_sdk/raw/master/SDK/projects/app_gatt_all_roles_jtag/BK3633_JTAG%E8%B0%83%E8%AF%95%E8%AF%B4%E6%98%8E.pdf),
  retrieved 2026-08-16: 504,950 bytes, SHA-256
  `de13956322b1ae6cd792308e3bb525705e9a02a17c511bc2aaee25301da9b183`.
- [Adafruit FT232H breakout](https://www.adafruit.com/product/2264), checked
  2026-08-16: MPSSE SPI/I2C/UART/JTAG, GPIO, 3.3 V output, and Linux support.
- [Core Electronics FT232H listing](https://core-electronics.com.au/adafruit-ft232h-breakout-general-purpose-usb-to-gpio-spi-i2c.html),
  checked 2026-08-16: `ADA2264`, AUD 27.80, listed in stock.
- [`ftdi-embedded-hal`](https://crates.io/crates/ftdi-embedded-hal), version
  0.24.0 checked 2026-08-16: Rust `embedded-hal` implementation with
  `libftdi` and vendored-backend features.
- [ESP32 BK3431Q/BK3432 programmer](https://oshwhub.com/findie/bk343x-shao-lu-di-ban),
  updated 2024-03-27 and retrieved 2026-08-16: captured Beken SPI protocol and
  GPL-3.0 source attachment; related-chip evidence only.
