# Custom-firmware and recovery gates

Last checked: 2026-08-14

## Verdict

| Gate | Current result | Confidence |
| --- | --- | --- |
| Can a custom image be delivered? | **Yes.** A modified, correctly checksummed stock-derived image was accepted and booted. | High |
| Can an interrupted official update be recovered over USB? | **Yes, while the resident loader remains active.** | High |
| Does a cold boot with an invalid application force the USB loader? | **Unknown.** | Low |
| Can custom code directly force the resident loader? | **Yes.** Direct MMIO recovery and subsequent reflash passed. | High |

Firmware analysis is still worthwhile: the update path is not cryptographically locked. Official USB recovery has been demonstrated after application erase, and custom code has directly entered that loader through the reconstructed MMIO path. The minimal standalone candidate still needs its reset/vector/startup path tested on hardware.

## Required scope

Only wired USB operation needs to survive. A custom implementation may omit Bluetooth, the 2.4 GHz dongle protocol, wireless pairing, and battery-powered operation. This substantially reduces the reproduction effort, but does not remove the need to preserve or forcibly enter the USB bootloader.

## Intended development workflow

The preferred workflow is closed-case USB development: compile an application, upload it through the resident USB loader, reset, and stream raw sensor data and diagnostic logs back over USB. A USB HID or CDC debug channel can provide Arduino-like iteration without JTAG. True live breakpoints and memory inspection would still normally require the rear JTAG pads.

Updater compatibility is a custom-firmware requirement. A standalone application should retain normal USB identity `047d:80d7`, the updater-facing vendor HID interface with 17-byte report ID `0x08`, its one-byte checksum, and command `0x0d` semantics. That allows Kensington's updater to request the resident loader and restore stock firmware. Sensor processing and diagnostics can use other commands or an additional interface without changing this recovery contract.

This requirement does not force the custom firmware to reproduce Bluetooth, 2.4 GHz operation, Kensington's mouse-processing code, or the complete vendor command set. It only preserves the small host-to-loader handoff interface. The resident loader remains below application address `0x2000` and must never be included in custom application writes.

A robust custom layout could retain the vendor loader below `0x2000`, place a small recovery shim first in the application region, and put experimental sensor code after that shim. The shim should enter USB recovery before experimental code when a button is held, when a host command is received, or after repeated watchdog failures. This is a design target, not yet a demonstrated capability on this board.

## Bootloader update boundary

The official USB update does **not appear to modify the bootloader**:

- The updater discards the first `0x2000` bytes of its resource and addresses every transmitted data block at `0x2000` or above.
- The transmitted resource contains no replacement data for addresses below `0x2000`.
- A normal application and boot device are handled separately; the boot device has generic VID/PIDs distinct from the Kensington application.
- The skipped prefix is meaningful: offsets `0x1000` onward contain Thumb code and a USB descriptor for boot VID/PID `25A7:FABE` at file offset `0x1710`. Releases 4.48 and 4.49 have identical code in this prefix; only a four-byte metadata/checksum field at `0x1f70` changes.
- The application has separate metadata at `0x2010` and an ARM vector table at `0x2020`.

This is high-confidence evidence that ordinary application updates preserve the first 8 KiB. It does not prove that this region is immutable ROM: a low-level JTAG/SPI operation might still alter it. A custom uploader should retain the same lower address boundary.

The embedded loader code makes further offline analysis possible and gives a known vendor loader image for low-level recovery. The live test proves that an already-running loader survives an interrupted application erase and can accept a fresh update. It does **not yet prove** that a cold boot with an invalid application automatically enters that loader.

## Live loader-entry result

A read-only/transition test has now proved that the normal application accepts the official reset-to-update packet and enumerates the resident loader as `25A7:FABE`. The loader remains reachable with the battery disconnected and USB as its only power source. It periodically re-enumerates while idle.

No non-writing exit command was found: loader command `0x0d`, a cable reconnect, and a complete battery-plus-USB power removal all returned to loader mode. Static analysis shows only `B0` (prepare), `B1` (data), and `B2` (identify) in its command dispatcher; the normal application launch follows successful final-block validation.

The official recovery cycle is now demonstrated. A first host attempt stopped after erase began and before sending any `B1` block. The loader stayed reachable. A corrected attempt resent `B0`, wrote and verified all 3,748 blocks of the exact v4.49 payload, and returned the device to normal `047D:80D7`, firmware `4.49`. The user confirmed normal ball, scroll, and button operation. The battery remained disconnected throughout.

## Evidence for custom images

- The official updater sends a raw 119,920-byte executable payload to address `0x2000`.
- Its prepare command supplies payload length and CRC-32, followed by 32-byte address/data packets that the loader echoes for host verification.
- The host calculates the CRC from the supplied payload; it does not compare the image against a fixed v4.49 hash.
- No signature or public-key material appears in the host protocol. The 4.48 and 4.49 images differ at only 26 byte positions, which is inconsistent with an ordinary large digital-signature block.
- Both changing header fields are now identified and reproduced as Beken image CRC-32 values.
- Loader disassembly shows `B0` erasing the application region, `B1` enforcing address bounds and read-back, and the final block checking the host-supplied payload CRC. No image-signature comparison appears in this loop.

This means creating and transmitting a replacement image looks feasible. Reproducing hardware initialization and the Bluetooth/2.4 GHz stacks may be much harder than bypassing the updater.

The acceptance question is now live-proven: a descriptor-only modification booted and reported `bcdDevice 4.50`. It retained the stock command-`0x0d` recovery path, and the user confirmed normal ball movement, buttons, and scrolling.

## Evidence for recovery

- Physical inspection confirmed that the controller is marked `BK3635UQN56A` (`AU334KX` on the second line).
- Normal updates start at `0x2000`, leaving the first 8 KiB untouched. This strongly suggests a resident boot/update region.
- The official updater asks the running application to reset into update mode. USB-only recovery is therefore not guaranteed if the application cannot run.
- [Beken's BK3635 specification](https://www.bekencorp.com/en/goods/detail/cid/46.html) states that the chip has 160 KiB embedded flash, read-out protection, JTAG debugging, and SPI flash download.
- [FCC internal photographs](https://fccid.io/GV3M01627-M/Internal-Photos/Internal-Photos-6181610) show board pads labeled `RSTN`, `P04`, `P05`, `P06`, `P07`, `VCC`, and `GND`. Their arrangement matches a likely factory programming/debug connection, but the exact BK3635 mapping is not yet verified.
- User photographs in [`images/`](../images/) independently confirm the same populated pad cluster and its dedicated signal traces.

Read-out protection may prevent making a complete backup. It does not by itself prove that erase and reprogramming are blocked, but the exact protection state of this product is unknown.

## Staged recovery work

1. The stock-derived USB `bcdDevice 4.50` acceptance probe passed.
2. The exact [stock recovery carrier](recovery-carrier.md) passed its direct read, watchdog reset, full marker/recovery, loader query, and complete reflash tests.
3. The minimal stub passes offline stock/disassembly and corruption tests, and its critical MMIO recovery path is independently proven on hardware by the carrier.
4. The [reset trampoline](reset-trampoline.md) booted successfully as version `4.52`, proving custom ARM code at reset while retaining the stock application and all carrier recovery commands.
5. The [startup trampoline](startup-trampoline.md) booted successfully as version `4.53`, proving the supervisor-mode, stack, and ARM/Thumb transition path.
6. The exact 420-byte standalone recovery stub booted, wrote the marker, reset into a new resident-loader enumeration, answered `B2 d2`, and was replaced successfully with v4.53.
7. Preserve the first 8 KiB boot region in every USB update.
8. Keep pad mapping/JTAG/SPI recovery as a separate hardware fallback investigation.

## Rotatrix fallback distinction

- [Rotatrix Wired](https://rotatrix.com/wired/kit/) replaces the Kensington controller board and connects the existing ribbon cables to the replacement board. A bricked stock controller should not prevent the trackball from operating through this kit, although it would not repair the original board.
- [Rotatrix Hybrid](https://rotatrix.com/kit/) is an add-on controller soldered alongside the Kensington controller. Its installation checks explicitly require a healthy stock unit in wired mode, so it should not be treated as a guaranteed fallback for broken Kensington firmware.
