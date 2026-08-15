# Stock recovery carrier

Last checked: 2026-08-14

## Purpose

This is the safer live-test candidate before the standalone recovery stub. It keeps stock v4.49 intact and injects 264 bytes into the verified zero-filled gap `0x21ac–0x22ff`. The injection ends at `0x22b4`, leaving 76 zero bytes before the unchanged stock IRQ handler at `0x2300`.

The normal vendor dispatcher is changed only to route four commands through the carrier:

| Command | Action | Expected recovery after failure |
| --- | --- | --- |
| `0x0d` | Tail-call original stock function `0x1895d` | Proven stock USB loader entry |
| `0x0e` | Non-writing space-1 read command through direct MMIO | Power cycle returns to stock carrier |
| `0x0f` | Direct watchdog reset, without marker | Normal stock carrier boots again |
| `0x10` | Direct erase, marker writes, delay and reset | Power cycle reaches either stock carrier or loader |

The read probe intentionally ignores the data value. Receiving the normal HID response proves that address setup, unlock words, keys, command `0x20`, start, busy polling and cleanup all returned without modifying storage.

## Offline result

The carrier preserves the original 128,112-byte container and 119,920-byte/3,748-block wire geometry. Both image CRCs are valid and USB `bcdDevice` is `4.51` for identification.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Injected code | 264 | `6dfab1b623c6fbd8daa6be71bdb3bfad1e90808da90956dc671c0165544dbd2e` |
| Full container | 128,112 | `e555d5e17edc84cb8799d035d6193f6f664c1df9116bcba3c49faef1609221e8` |
| Transmitted payload | 119,920 | `aac81065cc171f263d54c4bb64019bd2fa250d032640fcd7415fbb4caf8b2899` |

Updater payload CRC is `cbd4f74b`. The Rust recovery-carrier verifier checks
the stock source hash, exact derivation, dispatch branches, original recovery
pointer, injection bounds, IRQ preservation, critical MMIO literals and
ordering, code hash, headers, and wire geometry. Corruption tests require
rejection.

## Live flash result

On 2026-08-14 the exact audited carrier was flashed through the resident `25a7:fabe` loader. Its `B2` query returned BK3635 device type `d2`; the loader accepted the erase, echoed all 3,748 data blocks, validated payload CRC `cbd4f74b`, and returned on the same physical USB path as `047d:80d7` with `bcdDevice 0451`. Normal movement, buttons, and scrolling remained functional.

Carrier command `0x0e` then returned `080e01000000000000000000000000003e`: the command byte was preserved, byte 2 reported success (`01`), and the response checksum remained valid. This verifies that the direct non-writing storage-controller sequence completed and returned through the stock USB handler.

Carrier command `0x0f` then ran the direct watchdog-reset sequence. The same physical USB path returned as carrier `0451`, with USB device number changing from 21 to 22. No update marker was written.

Carrier command `0x10` then ran the direct sector erase, marker writes, delay, and watchdog reset. The same physical path enumerated as resident loader `25a7:fabe` with device number 23. Its `B2` query returned BK3635 type `d2`. The exact carrier was reflashed through that recovered loader; all 3,748 blocks echoed, payload CRC `cbd4f74b` passed, and carrier `0451` returned with device number 25. This live test verifies the complete custom-code MMIO recovery path and subsequent USB restoration.

After restoration, normal movement, buttons, and scrolling were confirmed again.

The Rust host utility rejects any container or payload differing from the
audited values above. It also requires the full container hash as explicit
confirmation before reaching the loader erase step.

## Guarded live sequence

The historical live sequence was:

1. Use stock command `0x0d` to enter the proven resident loader.
2. Flash the exact carrier with `flash-recovery-carrier`; require normal USB identity `047d:80d7` and `bcdDevice 0451` afterward.
3. Run `carrier-read-probe --confirm`. It accepts only a 17-byte command-`0x0e` response whose checksum is valid.
4. Run `carrier-reset-probe --confirm`. It accepts only a carrier `0451` re-enumeration on the same physical USB path with a changed device number.
5. Run `carrier-full-recovery --confirm-action ERASE-MARKER-RESET`. It accepts only a known loader identity on the same physical USB path.
6. Query that loader before any restore. The recorded official v4.49 image remains the hash-locked recovery image.

The utility resolves the USB parent of the selected `hidraw` node before every carrier-stage command. A stock v4.49/v4.50 application, a carrier on another path, or a device whose USB version is not `0451` is rejected. It exposes no arbitrary carrier command byte.

If the read or reset-only stage does not report success, stop and power-cycle rather than advancing. Both stages leave the application image and update marker unchanged. Stock command `0x0d` remains available from a running carrier regardless of the direct-MMIO results.

## Remaining risk

The intended MMIO path is now live-proven, including recovery and a complete reflash. This does not guarantee safety against future code accidentally writing application or boot flash, so exact address, command, and bounds checks remain necessary in every standalone-stub build.
