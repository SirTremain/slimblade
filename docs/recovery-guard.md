# Marker-first recovery guard

Last checked: 2026-08-14

## Design

The first permanent-guard candidate derives from the exact standalone recovery
stub that ran successfully. It keeps every executed byte through loader-marker
completion and the stock-equivalent delay. Its final Thumb call changes from
watchdog reset at `0x20fc` to experimental entry `0x21c4`.

The initial experiment is deliberately only `b .`, a two-byte infinite loop.
The expected live test is therefore: application USB disappears, the device
hangs, and a physical power cycle enters resident loader `25a7:fabe` because the
marker was already written. No experimental build will clear that marker until
it has its own proven USB recovery interface.

## Offline result

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Raw code | 422 | `93eef0420d1a54e4ca7efbfa1ca6a30e79044ff91b4294584ab062b7c6e061c0` |
| Full container | 128,112 | `7bb3055bc1575bcb9ca4eab9ba2a83a3dbaba131e92cca78fffb18397cc2d19a` |
| Transmitted payload | 119,920 | `3c11672dca070a246202b70b743456b4b5bb32b157d2e305e2f032499e36823c` |

Only seven container bytes differ from the live stub: four application-CRC
bytes, one branch-displacement byte, and the two experimental instruction bytes.
Application CRC is `f37fac2d`; updater payload CRC is `2b64f82e`. The verifier
requires the exact live-stub base,
reconstructs the guard independently, checks the complete difference set,
decodes both final call targets, and requires erased padding after the hang.

## Live result

Verified on 2026-08-14 with the battery disconnected:

- The resident `25a7:fabe` loader accepted all 3,748 payload blocks and the
  guard payload CRC `2b64f82e`.
- The application then remained USB-silent, matching its deliberate Thumb
  self-loop.
- After complete USB power removal and reconnection, the resident loader
  returned and answered the non-writing `B2` query with device type `d2`.
- The loader accepted all 3,748 blocks of the proven v4.53 image (container
  SHA-256 `dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`)
  and returned as `047d:80d7`, `bcdDevice=0453`.
- The user then confirmed normal ball movement, scrolling, and button behavior.

This proves the persistent marker is committed before the experimental entry
and is honored during a true cold boot. It also proves recovery can restore a
working application after that experimental entry hangs.

## Remaining risks

- Failure before the marker completes would still prevent automatic loader
  entry. That executed prefix is byte-identical to the live-proven stub and has
  now succeeded in both the standalone-stub and guard tests.
- Experimental code must not alter loader-marker storage, application flash, or
  the untouched first 8 KiB.
- Clearing the marker will remain forbidden until a separate recovery trigger
  and custom USB path have both passed on hardware.
