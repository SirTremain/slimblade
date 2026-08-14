# SlimBlade Pro firmware research

Last checked: 2026-08-14

## Current result

The stock SlimBlade Pro uses two optical sensors but exposes ball twist as discrete HID wheel input, not as a continuous Z-rotation axis. A third-party controller is currently required to obtain the raw sensor data needed for continuous three-axis reconstruction.

The device is field-upgradable over its wired USB connection. The official v4.49 Windows package contains a 3,008,000-byte .NET updater and a **128,112-byte** embedded image. Decompilation shows that the updater skips the first 8,192 bytes and sends **119,920 bytes** to flash address `0x2000`.

## Inspected artifacts

Artifacts were downloaded from ACCO Brands Japan and inspected in temporary storage; they are not committed here.

| Version | Artifact | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| 4.49 | ZIP package | 1,037,410 | `dffe13ab063cb9614669914295b273bda0e5906bc5af75b3f73cd2da5f0f41ac` |
| 4.49 | Updater EXE | 3,008,000 | `38fc1b333d316039e4eb732c70183b8c6c4cc831c90246425917e9dce64f7688` |
| 4.49 | Embedded firmware resource | 128,112 | `e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7` |
| 4.48 | ZIP package | 1,057,088 | `2df13ade70d76621d8283d956bbd8ee402932cc5de21670b19567b63c2241819` |
| 4.48 | Updater EXE | 3,008,000 | `d47f96ce5dfedc87cf0b7c030b6b9d25c95551c9647b72150ff29fba4183d060` |
| 4.48 | Embedded firmware resource | 128,112 | `aa648a9b71e444eb388b8d6a21503ffe937d7f5e50e8fb14bc74034d25f741a4` |

Official package URLs:

- v4.49: <https://accobrands.co.jp/wp/wp-content/uploads/Kensington-Slimblade-Pro-V4.49.zip>
- v4.48: <https://accobrands.co.jp/wp/wp-content/uploads/Kensington-Slimblade-Pro.zip>

## Updater observations

- The executable identifies itself internally as `USBUpdateTool.exe` and is a 32-bit .NET assembly.
- The embedded image is named `USBUpdateTool.MakeUpgradeTool.Files.CompxUpgradeBinFile.bin`.
- The embedded configuration names the image `BK3635-MS-606OR-3220-sensor-AES-B3D759-EEPROM125-V4.49-2023.03.03.bin`, specifies SlimBlade USB VID/PID `047D:80D7`, and selects IC index `00`.
- In the updater code, IC index `00` constructs `BK3635_APPUsb` and `BK3635_UsbPacket`.
- Physical inspection of the research device confirmed package marking `BK3635UQN56A`, with secondary marking `AU334KX`. Beken documents the BK3635 QFN56 variant as a 7 x 7 mm, 56-pin package; no authoritative decoding of the extra suffix or secondary traceability code has been found.
- Both inspected versions use the same 128,112-byte resource size, but the contents and hashes differ.
- `SetFileDownloadAddr(8192)` removes the image prefix. Data packets carry 32 bytes each and add base address `0x2000` to the packet offset.
- The prepare packet contains the payload length and a CRC-32 using polynomial `0xEDB88320`; packet framing also uses a simple byte checksum.
- The updater calculates that CRC from the selected payload rather than comparing it with a hard-coded v4.49 hash.
- The image contains unencrypted executable code and readable USB descriptors. Versions 4.48 and 4.49 differ at only 26 byte positions.
- No public-key signature or signature field was found in the updater protocol. Two changing four-byte header values remain unexplained, so acceptance of an altered image is not yet proven.
- The running application receives a HID command that resets it into update mode. It is not yet known whether a corrupt application can enter that mode by reset or pin strapping alone.
- The updater distinguishes a normal device from a boot device. For this BK3635 mouse class it recognizes boot HID paths containing `25A7:FABE`, `3554:F600`, or `3554:F800`; the normal SlimBlade application uses Kensington `047D:80D7`. If a hardware entry method is found, this VID/PID change provides a direct confirmation that it worked.

## Evidence and open work

- Kensington/Lenovo product description: [dual-sensor ball-twist scrolling](https://www.lenovo.com/us/en/p/accessories-and-software/keyboards-and-mice/mice/78531292).
- Rotatrix states that the [stock controller does not expose the raw sensor data](https://rotatrix.com/), so its modification reads both sensors with another controller.
- The official update instructions require a data-capable USB cable and wired mode, as recorded in this [contemporary firmware report](https://sundaygamer.net/slimblade-pro/).

Next useful checks:

1. Enter the official loader without writing and confirm its USB VID/PID and exit behavior.
2. Determine from loader analysis whether an absent or invalid application automatically leaves USB recovery available.
3. Identify the two changing four-byte header values and any device-side image validation.
4. Reproduce the host protocol and compile a minimal application for address `0x2000`.
5. Test image acceptance only after a satisfactory closed-case or pad-based recovery path has been demonstrated.
