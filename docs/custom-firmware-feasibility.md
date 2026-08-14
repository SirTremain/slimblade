# Custom-firmware and recovery gates

Last checked: 2026-08-14

## Verdict

| Gate | Current result | Confidence |
| --- | --- | --- |
| Can a custom image be delivered? | **Probably.** No hard blocker has been found. | Medium |
| Can a broken application be recovered? | **Probably by hardware, but not yet demonstrated.** | Medium-low |
| Flash the only available device? | **No-go until recovery is demonstrated on spare hardware.** | High |

Firmware analysis is still worthwhile: the update path does not presently look cryptographically locked. Flashing the user's only unit is not justified yet because the recovery path lacks an exact pin map and a tested programmer procedure.

## Required scope

Only wired USB operation needs to survive. A custom implementation may omit Bluetooth, the 2.4 GHz dongle protocol, wireless pairing, and battery-powered operation. This substantially reduces the reproduction effort, but does not remove the need to preserve or forcibly enter the USB bootloader.

## Intended development workflow

The preferred workflow is closed-case USB development: compile an application, upload it through the resident USB loader, reset, and stream raw sensor data and diagnostic logs back over USB. A USB HID or CDC debug channel can provide Arduino-like iteration without JTAG. True live breakpoints and memory inspection would still normally require the rear JTAG pads.

A robust custom layout could retain the vendor loader below `0x2000`, place a small recovery shim first in the application region, and put experimental sensor code after that shim. The shim should enter USB recovery before experimental code when a button is held, when a host command is received, or after repeated watchdog failures. This is a design target, not yet a demonstrated capability on this board.

## Bootloader update boundary

The official USB update does **not appear to modify the bootloader**:

- The updater discards the first `0x2000` bytes of its resource and addresses every transmitted data block at `0x2000` or above.
- The transmitted resource contains no replacement data for addresses below `0x2000`.
- A normal application and boot device are handled separately; the boot device has generic VID/PIDs distinct from the Kensington application.
- The skipped prefix is meaningful: offsets `0x1000` onward contain Thumb code and a USB descriptor for boot VID/PID `25A7:FABE` at file offset `0x1710`. Releases 4.48 and 4.49 have identical code in this prefix; only a four-byte metadata/checksum field at `0x1f70` changes.
- The application has separate metadata at `0x2010` and an ARM vector table at `0x2020`.

This is high-confidence evidence that ordinary application updates preserve the first 8 KiB. It does not prove that this region is immutable ROM: a low-level JTAG/SPI operation might still alter it. A custom uploader should retain the same lower address boundary.

The embedded loader code makes further offline analysis possible and gives a known vendor loader image for low-level recovery. It does **not yet prove** that a unit with an invalid application will automatically enumerate that loader over USB; that behavior remains the decisive closed-case recovery question.

## Evidence for custom images

- The official updater sends a raw 119,920-byte executable payload to address `0x2000`.
- Its prepare command supplies payload length and CRC-32, followed by address/data packets with simple checksums.
- The host calculates the CRC from the supplied payload; it does not compare the image against a fixed v4.49 hash.
- No signature or public-key material appears in the host protocol. The 4.48 and 4.49 images differ at only 26 byte positions, which is inconsistent with an ordinary large digital-signature block.
- Two changing four-byte header fields are still unidentified. Device-side authentication or another checksum cannot yet be ruled out.

This means creating and transmitting a replacement image looks feasible. Reproducing hardware initialization and the Bluetooth/2.4 GHz stacks may be much harder than bypassing the updater.

## Evidence for recovery

- Physical inspection confirmed that the controller is marked `BK3635UQN56A` (`AU334KX` on the second line).
- Normal updates start at `0x2000`, leaving the first 8 KiB untouched. This strongly suggests a resident boot/update region.
- The official updater asks the running application to reset into update mode. USB-only recovery is therefore not guaranteed if the application cannot run.
- [Beken's BK3635 specification](https://www.bekencorp.com/en/goods/detail/cid/46.html) states that the chip has 160 KiB embedded flash, read-out protection, JTAG debugging, and SPI flash download.
- [FCC internal photographs](https://fccid.io/GV3M01627-M/Internal-Photos/Internal-Photos-6181610) show board pads labeled `RSTN`, `P04`, `P05`, `P06`, `P07`, `VCC`, and `GND`. Their arrangement matches a likely factory programming/debug connection, but the exact BK3635 mapping is not yet verified.
- User photographs in [`images/`](../images/) independently confirm the same populated pad cluster and its dedicated signal traces.

Read-out protection may prevent making a complete backup. It does not by itself prove that erase and reprogramming are blocked, but the exact protection state of this product is unknown.

## Recovery proof required before flashing

1. Confirm the programming-pad mapping without writing flash.
2. Establish communication through the pads and identify the required voltage and programmer.
3. Prove that a blank or deliberately broken application can be erased, programmed, and verified without altering the first 8 KiB.
4. Preserve the first 8 KiB boot region unless a complete known-good image and full-chip recovery method exist.

No device has been flashed or electrically probed during this research.

## Rotatrix fallback distinction

- [Rotatrix Wired](https://rotatrix.com/wired/kit/) replaces the Kensington controller board and connects the existing ribbon cables to the replacement board. A bricked stock controller should not prevent the trackball from operating through this kit, although it would not repair the original board.
- [Rotatrix Hybrid](https://rotatrix.com/kit/) is an add-on controller soldered alongside the Kensington controller. Its installation checks explicitly require a healthy stock unit in wired mode, so it should not be treated as a guaranteed fallback for broken Kensington firmware.
