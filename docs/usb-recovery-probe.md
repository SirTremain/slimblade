# USB recovery probe

Last checked: 2026-08-15

## Verified on the host

- The first 420 code bytes exactly match the live-tested marker-first guard.
  The marker is written before any experimental Rust runs.
- The corrected 3,212-byte experiment uses only typed stock-observed platform,
  clock, interrupt-control, and USB MMIO. Its 14 decoded MMIO loads are
  allowlisted; storage, marker, reset-controller, panic, allocation,
  compiler-helper, indirect-jump, and escaping-branch checks pass.
- Endpoint 0 reproduces Kensington's CSR0-high `01`, CSR0-low `0a` OUT-status
  sequence. Fake-device tests cover enumeration, address 7, configuration 1,
  the exact 17-byte `08 0d` report, and loader entry only after status
  completion.
- `cargo xtask usb-probe` rebuilds and hash-locks both code and container. The
  CLI accepts the container only through `flash-usb-recovery-probe` with its
  exact SHA-256 confirmation; no command invokes it automatically.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Code | 3,632 | `cbe5bbbb119885f9d5b861b5548371a80672ada9b0ad9014069f12c8e41a9eca` |
| Container | 128,112 | `3ce23e3b9af4a1e713bad622f56fc9055cb178ca1ec198c7556c1dee44169e5a` |
| Updater payload | 119,920 | `6e14eedaa65930bca93fa60febd43f966f310743c9c4c7c79084865990192f7d` |

Payload CRC is `2da6b921`; maximum recorded stack frame is 184 bytes. Generated
artifacts remain ignored under `firmware/bk3635-usb-probe/target/probe/`.

## Inference

A tight polling loop should service latched endpoint-zero events quickly enough
while the CPU remains interrupt-masked. This is the main material hardware
assumption left after reproducing Kensington's controller bring-up.

## Hardware stages

The exact first container, SHA-256
`d08395311afb43a289b05bbd0fb31a750c62371e957eedde4c08f0e7c78560e8`,
was flashed on 2026-08-15 through resident loader
`25a7:fabe`; its non-writing query returned `d2`, and all 3,748 payload blocks
echoed successfully with CRC `8bb70620`. The device then disappeared from USB
without enumerating as expected `047d:80d7`/`0454`. Command `0x0d` was not sent.

After USB power was removed for five seconds, the same physical port returned
as resident loader `25a7:fabe`; its non-writing query again returned `d2`.
This verifies that the marker-first recovery guard survived the failed USB
experiment and recovered the device as designed.

Verified: transfer, marker-first startup, and subsequent power-cycle recovery
all worked. Inference: the polling USB experiment failed during controller
startup or initial enumeration.

The exact audited v4.53 startup-trampoline image was then restored. All 3,748
blocks echoed, and the device returned on the same physical port as
`047d:80d7`, `bcdDevice 0453`, with its 170-byte report descriptor. Its
128,112-byte container SHA-256 was
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`.

## Failure analysis and correction

Verified from disassembly: Kensington's 190-byte USB initializer at
`0x17f54` is byte-identical in the inspected v4.48 and v4.49 containers; the
v4.49 slice SHA-256 is
`9d6958b9096fab5608fea9c19519215090bbcc3772a940162dd1ecd0409bbbfb`.
The first Rust probe incorrectly treated the related BK3633 SDK sequence as
the stock BK3635 sequence. It toggled SDK system register `0x0080000c` and
asserted `0x00804098` bit 0, neither of which Kensington's routine does. It
also omitted Kensington's `0x00806520`/`0x00806524` platform setup,
`0x00800020` clock preparation, high interrupt-mask bytes, DMA-endpoint clear,
function-address clear, `DEVCTL` activation, module/global enable writes, and
final OTG/POWER activation.

Inference: asserting the non-stock reset bit or omitting the final controller
activation is the most likely reason the first probe never attached to USB.
Because several mismatches existed, the failed hardware run cannot isolate one
register as the sole cause.

The corrected Rust initializer now reproduces Kensington's register operations
and ordering, including equivalent 499-iteration delays. Its fake-register test
checks the entire operation transcript. The post-link audit confirms the exact
marker prefix, reviewed MMIO literals, bounded branches and stack, and absence
of storage/reset-controller access.

The corrected container was flashed on 2026-08-15. Resident loader
`25a7:fabe` returned `d2`, and all 3,748 blocks echoed with payload CRC
`2da6b921`, but the device again failed to enumerate; command `0x0d` was not
sent. A five-second USB power cycle returned the same port to loader
`25a7:fabe`/`d2`, verifying marker recovery a second time. The exact v4.53
image was restored with 3,748 echoed blocks and returned as `047d:80d7`,
`bcdDevice 0453`, with its 170-byte report descriptor.

Inference: Kensington's USB routine depends on earlier stock system and RAM
initialization, or its FIQ service path is required before enumeration. Exact
controller-register replay alone is insufficient. The safer next experiment
is a marker-first harness that resumes complete stock startup and retains the
stock USB stack before invoking any custom Rust. That build-only harness is now
hash-locked and audited in [`stock-harness.md`](stock-harness.md); it has not
been flashed.

CSR evidence comes from Kensington v4.49 disassembly and the vendored
[Beken BK3633 BLE SDK](https://gitee.com/beken-corp/bk3633_ble_sdk) commit
`0a461f8ed4a4f17ff6889d6f9d34e521b92b8243`, retrieved 2026-08-14. The SDK
provenance and deterministic tree hash are recorded in
[`../vendor/bk3633_sdk/UPSTREAM.md`](../vendor/bk3633_sdk/UPSTREAM.md).
