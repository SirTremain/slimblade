# BK3635 USB recovery probe

Marker-first firmware for wired endpoint-zero enumeration and command `0x0d`.
The task runner creates code and container files prefixed `DO_NOT_FLASH`; no
build command writes hardware.

Run `cargo xtask usb-probe` from the repository root. The gate rebuilds the
live-tested guard, requires an exact 420-byte prefix, and audits actual
PC-relative MMIO loads, symbols, control flow, stack sizes, storage/marker
words, byte count, and SHA-256.

Verified host build on 2026-08-15: 3,556 bytes, 3,136 experimental bytes,
maximum stack frame 176 bytes, SHA-256
`9bd0c0d1e6b57583be3ad91f9f444101bdf693359e499a0e4f417ca0e51c9b67`.
The 128,112-byte container SHA-256 is
`d08395311afb43a289b05bbd0fb31a750c62371e957eedde4c08f0e7c78560e8`.
No hardware test has been performed. See
[`../../docs/usb-recovery-probe.md`](../../docs/usb-recovery-probe.md).
