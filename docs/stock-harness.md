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

## Live result

The exact `cac3bab3…e3b356` container was flashed on 2026-08-15. Stock v4.53
first entered resident loader `25a7:fabe` through command `0x0d`; the loader's
non-writing query returned `d2`. All 3,748 blocks echoed successfully and the
loader accepted payload CRC `2b53d16e`. The same physical USB path returned as
`047d:80d7`, `bcdDevice 0455`, with the expected 170-byte vendor descriptor.

This verifies the combined marker writer, ARM/Thumb transitions, return to
Kensington startup, and normal stock USB enumeration. The user then confirmed
normal ball movement, scrolling, and button behavior.

Stock command `0x0d` was then sent from the live `0455` vendor interface. The
same physical USB path returned as resident loader `25a7:fabe` with a changed
device number, and its non-writing query returned `d2`. No erase or flash was
performed during this command test. This verifies the fast software recovery
route while the application USB stack remains functional.

The exact harness was reflashed from that loader; all 3,748 blocks echoed,
payload CRC `2b53d16e` passed, and application `0455` returned. After complete
USB power removal for five seconds, the same physical path returned as working
application `047d:80d7`, `bcdDevice 0455`, rather than resident loader. The
170-byte descriptor remained intact.

Verified result: complete Kensington startup makes the early marker ineffective
for the next cold boot. The harness remains recoverable through software
command `0x0d` while USB works, but it is not a permanent fallback for a later
custom-code hang.

## Not yet verified

- Whether the early storage transaction failed before stock initialization or
  stock initialization later replaced its contents.
- Whether a late marker written from an explicit USB-triggered experimental
  entry remains effective across a subsequent cold boot.

No current build or test command accesses hardware.

The next safer design should boot stock normally, then use an explicit USB
command to write the marker immediately before entering experimental code. A
hang after that late marker can be cold-boot tested without allowing stock
startup to run between the marker write and the failure. This remains an
unbuilt design, not a verified recovery path.
