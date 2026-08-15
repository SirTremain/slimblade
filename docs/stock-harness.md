# Marker-first stock-startup harness

Last checked: 2026-08-15

## Purpose

The standalone USB probes failed before enumeration even after matching
Kensington's controller-register sequence. This narrower experiment retains
the complete v4.53 Kensington startup, FIQ/IRQ handlers, USB stack, and stock
command `0x0d`. Custom code runs only before stock reset continuation `0x2068`.

The startup path writes the live-proven persistent loader marker first. If
stock USB returns, command `0x0d` provides the fast software route back to the
resident loader. If startup fails, a true USB power cycle remains the fallback.
Experimental code must not access persistent storage; the invariant in
[`recovery-guard.md`](recovery-guard.md) remains unchanged.

## Verified offline

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Linked injection | 340 | `a26b3d8d9d2b45a79ccb80792d3dd8b5e40d47a07e539bc0e88ef72c9fc7c981` |
| Full container | 128,112 | `cac3bab34545a2e20ad545af5b91c4a55db1c9cacfdcb0f45e4a348b65e3b356` |
| Updater payload | 119,920 | `2b2d8fa2ceacb3429e4624e19af506dcf6efb6a44614dc7bfe226f20adbe3e8b` |

Payload CRC is `2b53d16e`; proposed USB `bcdDevice` is `0455`. The exact base is
the live-tested v4.53 container with SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`.

The injection fills the verified `0x21ac–0x22ff` gap exactly:

- `0x21ac–0x22cb`: stock-compatible recovery dispatcher, marker writer,
  watchdog reset, storage helper, and literals;
- `0x22cc–0x22ff`: ARM startup trampoline;
- `0x2300` onward: original Kensington IRQ/FIQ wrappers, untouched.

The reset instruction at `0x2064` branches to `0x22cc`. The trampoline enters
Thumb marker code at odd address `0x221b`, restores ARM state at `0x22e8`, and
branches to stock startup at `0x2068`. It resets system interrupt control to
zero after the marker write, giving stock startup the same clean control value
used by the live-tested marker prefix.

`cargo xtask stock-harness` verifies the injection and v4.53 base hashes,
defined/undefined symbols, both ELF executable sections, every recovery
literal, both ARM branches, ARM/Thumb tagging, header CRCs, IRQ/FIQ bytes,
stock command-dispatch bytes, and the resulting container identity. Corruption
tests cover the base, injection, reset branch, and container.

## Not yet verified

- The `0455` container has not been flashed.
- Marker completion followed by full Kensington startup has not run on the
  BK3635 as one combined path.
- It is not yet verified that complete stock startup leaves the newly written
  marker intact. After successful `0455` enumeration, a separate cold-boot
  stage must return to `25a7:fabe` before this can be called a permanent
  post-startup fallback.
- Successful stock enumeration and command `0x0d` remain the live acceptance
  criteria. If enumeration fails, the expected recovery is resident loader
  `25a7:fabe` after complete USB power removal and reconnection.

No current build or test command accesses hardware.

The safest live sequence therefore has two independent stages: first verify
`0455` enumeration and stock command `0x0d`; then reflash the exact same image,
allow full startup, and cold-boot it to verify marker persistence through stock
initialization. Failure in either stage stops custom-hook development.
