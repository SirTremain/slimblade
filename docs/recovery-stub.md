# Recovery-stub path

Last checked: 2026-08-14

## Verified image contract

- BK3635 application header: 16 bytes at file/flash offset `0x2010`.
- Executable vector table: `0x2020`; reset target in stock v4.49: ARM-state `0x2064`.
- Header layout, little-endian: CRC-32, 16-bit version, 16-bit length in four-byte words, UID, CRC status, section status, ROM version.
- Application UID: `0x42424242`; combined stack/application UID at `0x1f70`: `0x53535353`.
- CRC: reflected polynomial `0xedb88320`, initial `0xffffffff`, no final XOR, covering all bytes after the 16-byte header through `header_offset + length_words * 4`.
- Both official SlimBlade v4.48 and v4.49 headers reproduce exactly with this rule.

[`tools/firmware_image.py`](../tools/firmware_image.py) inspects this structure and packages raw code linked for `0x2020`. It performs no USB access.

## CPU and build contract

The stock vector/startup code is ARM state with later ARM/Thumb interworking. A closely related Beken BK3633 SDK specifies `arm968e-s`, ARMv5TE, Thumb, and `arm-none-eabi-gcc`. Clang 22 on the research host accepts the same target. [`firmware/recovery_stub/`](../firmware/recovery_stub/) builds a minimal candidate using that contract. It has passed offline pre-flight checks but has not run as a standalone image on hardware.

The BK3635 product page only calls the core a 32-bit RISC MCU; ARM968E-S is therefore a strong family/source and binary inference, not an explicit BK3635 datasheet statement.

## Verified stock loader-entry path

The normal USB vendor dispatcher handles command `0x0d` at stock v4.49 address `0x18fba` and calls `0x1895c`. That function:

1. disables the watchdog;
2. erases the 512-byte secondary nonvolatile space at controller address `0x8000`;
3. writes `12 34 56 78 9a bc d2 19` at word addresses `0x807c` and `0x807d`;
4. returns the HID response, delays approximately 200 ms, and requests a watchdog reset.

The final marker byte is the firmware packet checksum `(0x55 - sum(first seven bytes)) & 0xff`. Controller operations encode storage space 1 in bits 5 and above: erase command `0x28`, write command `0x24`. Stock initialization describes space 0 as `0x25e00` bytes and space 1 as `0x200` bytes. This supports identifying space 1 as the BK3635's small EEPROM-like nonvolatile area rather than application flash.

The live command test already proved that this stock path changes `047d:80d7` into resident loader `25a7:fabe`. The distributed file contains a preserved loader suffix at offsets `0x1000–0x17cf`, including the update loop and USB descriptor. Its lower routines are absent/filled with `0xff`, so the early cold-boot marker comparison is not present in the package.

[`firmware/recovery_stub/bk3635_recovery.c`](../firmware/recovery_stub/bk3635_recovery.c) reconstructs this sequence without calling stock application addresses. The stock software guard words protect its flash-library calls; the stub bypasses those calls and reproduces their final MMIO sequence directly.

## Offline pre-flight result

The 2026-08-14 audit found and fixed two differences before any custom flash:

- The storage unlock words had been reversed. The emitted order now matches stock exactly: `0x58a9`, then `0xa958`.
- The C delay had matching loop counts but fewer cycles. It is now assembly with the stock executed instruction path for `(200, 0)`.

The hash-locked verifier compares the output against the exact official v4.49
image, live-proven v4.51 carrier, and live-tested v4.53 startup trampoline. It
checks the application header/CRC, vector geometry, normalized startup
operations, ARM-to-Thumb entry, complete internal call graph, loader marker,
erase/write commands, storage unlock and polling sequence, watchdog reset,
absence of writable allocated sections, erased padding, and wire geometry. The
address-independent 42-byte storage-controller core must be byte-for-byte
identical to the carrier code that passed on hardware. Negative tests corrupt
the CRC, padding, startup/stock/carrier references, reset stack load, call graph,
and unlock order and require rejection.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Raw code | 420 | `d88b2cd9211d9c46914062770e024f409dcee75ec826e70e80f6ff9a9e353bfe` |
| Full container | 128,112 | `34daf13778a79034cc3a35917fbe6cfacc0b2f93db650e50f1f4df98ecf7e618` |
| Transmitted payload | 119,920 | `67415f19bf43ea3f91fe1ec223bad5c69d3e6975cf42aba60219a8bfd1457ea6` |

Application CRC is `f96b816e`; updater payload CRC is `6e473ed7`. The payload
uses the same 3,748-block path as the successful stock-derived v4.50 probe.
`make preflight` currently passes 73 tests.

Three clean builds on 2026-08-14 produced identical raw-code, container, and
ELF bytes. The ELF SHA-256 is
`d97354a17c57b5e78160bf6313001ecff15b55edbd4d94e3aa1e85d2b166c679`.
The standalone reset and live startup trampoline normalize to the same five
operations—select supervisor mode, write CPSR, load stack, load entry, and
branch—with the same stack `0x00407f00`. Only their placement-dependent literal
offsets and intended Thumb destinations differ.

The [stock recovery carrier](recovery-carrier.md) live-proved the exact direct
MMIO sequence, including loader entry and a complete application reflash. The
startup trampoline subsequently live-proved the CPU-mode, stack, and
interworking assumptions.

The carrier, [reset trampoline](reset-trampoline.md), and
[startup trampoline](startup-trampoline.md) gates are complete. Together they
live-prove the direct recovery MMIO sequence, earliest reset hook,
supervisor-mode switch, standalone stack, and ARM/Thumb transitions. Only their
composition as the 420-byte standalone image was the final test gate.

## Live standalone result

On 2026-08-14 the exact 420-byte candidate was flashed from resident loader
device number 42. The loader accepted erase, echoed all 3,748 payload blocks,
and accepted payload CRC `6e473ed7`. The standalone application then executed
and the same physical USB port returned as a new `25a7:fabe` loader instance,
device number 43. Its non-writing `B2` response identified BK3635 type `d2`.

This proves the complete source-built vector, reset, ARM-to-Thumb entry,
storage erase and marker writes, stock-equivalent delay, and watchdog-reset path
executed together and entered the resident loader. It is the first standalone
replacement application in this investigation.

The returned loader then accepted restoration of the exact v4.53 startup
trampoline: all 3,748 blocks echoed and payload CRC `4e9c5e53` passed. The same
port returned as `047d:80d7`, `bcdDevice 0453`, device number 45, with its
170-byte vendor HID descriptor and stable symlink. User confirmation of normal
movement, buttons, and scrolling after restoration remains pending.

The guarded host command accepts only the exact container and payload hashes
above. After the final block, it requires a *new* known loader enumeration on
the same physical USB path, with disappearance or a changed USB device number;
the pre-flash loader instance cannot satisfy the result check.

## Lowest-risk acceptance probe

Before the minimal stub, the safer live candidate is a full stock v4.49 image with only USB `bcdDevice` changed from `4.49` to `4.50`. The application and combined-header CRCs are then regenerated. This preserves the proven stock mouse and command-`0x0d` recovery path while making custom-image acceptance observable in USB descriptors.

`tools/firmware_image.py make-v449-descriptor-probe` produces this artifact only from the exact recorded official v4.49 image. The deterministic temporary result is 128,112 bytes, SHA-256 `990079b8a71668f0e19963c71a70f8efac3f36e69a21133d60f9951cd8519081`; its transmitted payload is 119,920 bytes, SHA-256 `46520d851e5c908500e89f48fc05880c60fc43fb17367aeb6c109b3f0ce3ee88`, updater CRC `be3fedce`. It is not committed.

## Live modified-image result

On 2026-08-14, the hash-locked descriptor probe was flashed through `25a7:fabe`. The loader accepted prepare/erase, echoed all 3,748 `B1` blocks byte-for-byte, accepted the final CRC, and launched `047d:80d7` with `bcdDevice 0450`. Both normal mouse and vendor HID interfaces returned with their stock report descriptors. The user confirmed normal ball movement, buttons, and scrolling.

This proves that modified, correctly checksummed application firmware is accepted. The first attempt encountered `EIO` during the pre-erase `B2` query because the periodically re-enumerating loader invalidated the hidraw handle; no `B0` command had been sent. Reopening the current node succeeded. A flasher must distinguish this safe pre-erase retry case from any failure after `B0`.

The descriptor probe also removes the earlier small-container concern: the recovery candidate is padded to the exact stock application end (`0x1f470`) and follows the already-proven 119,920-byte transfer geometry.

## Sources

- [Beken BK3635 product page](https://www.bekencorp.com/en/goods/detail/cid/46.html), retrieved 2026-08-14: 160 KiB flash, 32 KiB RAM, JTAG/SPI download, full-speed USB.
- [Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk), commit `0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14. Relevant source SHA-256 values: image header `069f1d14ae189b33b1711c40c84d6f3055ab2ec4f7497daedaf30de7ce01f4d4`; GNU build flags `e3bf2d57861029a15be1bcb70c658a1be365f821de364be0a769cbc571bc6c99`; USB boot selection `c3c97da7b59d5ababf7ecb7ec773197c43d6dc092cfcf4aae6ff7174d397e735`.

The build-relevant SDK source is vendored under
[`vendor/bk3633_sdk`](../vendor/bk3633_sdk/README.md). Compiled SDK reference
artifacts were inspected in temporary storage and are not committed.
