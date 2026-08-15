# USB recovery probe

Last checked: 2026-08-15

## Verified on the host

- The first 420 code bytes exactly match the live-tested marker-first guard.
  The marker is written before any experimental Rust runs.
- The 3,136-byte experiment uses only typed system-power and USB MMIO. Its 11
  decoded MMIO loads are allowlisted; storage, marker, reset-controller, panic,
  allocation, compiler-helper, indirect-jump, and escaping-branch checks pass.
- Endpoint 0 reproduces Kensington's CSR0-high `01`, CSR0-low `0a` OUT-status
  sequence. Fake-device tests cover enumeration, address 7, configuration 1,
  the exact 17-byte `08 0d` report, and loader entry only after status
  completion.
- `cargo xtask usb-probe` rebuilds and hash-locks both code and container. The
  CLI accepts the container only through `flash-usb-recovery-probe` with its
  exact SHA-256 confirmation; no command invokes it automatically.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Code | 3,556 | `9bd0c0d1e6b57583be3ad91f9f444101bdf693359e499a0e4f417ca0e51c9b67` |
| Container | 128,112 | `d08395311afb43a289b05bbd0fb31a750c62371e957eedde4c08f0e7c78560e8` |
| Updater payload | 119,920 | `faccf0e7cf43f460c7241a08f92b11cc74f6c302f05eb177d8f3931e3b94522b` |

Payload CRC is `8bb70620`; maximum recorded stack frame is 176 bytes. Generated
artifacts remain ignored under `firmware/bk3635-usb-probe/target/probe/`.

## Inference

A tight polling loop should service latched endpoint-zero events quickly enough
without enabling the interrupt controller or FIQ. This is the only material
hardware assumption left in the first probe.

## Hardware stages

No hardware test has occurred. A future explicit flash request should first
observe only `047d:80d7`, `bcdDevice 0454`, and the descriptors. It should not
send command `0x0d` during that first stage. If enumeration succeeds, a later
explicit command test can request the resident loader. Removing and restoring
USB power remains the independent fallback because the marker precedes the
experiment.

CSR evidence comes from Kensington v4.49 disassembly and the vendored
[Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk) commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14. The SDK
provenance and deterministic tree hash are recorded in
[`../vendor/bk3633_sdk/UPSTREAM.md`](../vendor/bk3633_sdk/UPSTREAM.md).
