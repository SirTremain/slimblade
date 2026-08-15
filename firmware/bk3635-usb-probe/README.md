# BK3635 USB recovery probe

Marker-first firmware for wired endpoint-zero enumeration and command `0x0d`.
The task runner creates code and container files prefixed `DO_NOT_FLASH`; no
build command writes hardware.

Run `cargo xtask usb-probe` from the repository root. The gate rebuilds the
live-tested guard, requires an exact 420-byte prefix, and audits actual
PC-relative MMIO loads, symbols, control flow, stack sizes, storage/marker
words, byte count, and SHA-256.

Verified corrected host build on 2026-08-15: 3,632 bytes, 3,212 experimental
bytes, maximum stack frame 184 bytes, SHA-256
`cbe5bbbb119885f9d5b861b5548371a80672ada9b0ad9014069f12c8e41a9eca`.
The 128,112-byte container SHA-256 is
`3ce23e3b9af4a1e713bad622f56fc9055cb178ca1ec198c7556c1dee44169e5a`.
This corrected candidate has not run on hardware. See
[`../../docs/usb-recovery-probe.md`](../../docs/usb-recovery-probe.md).
