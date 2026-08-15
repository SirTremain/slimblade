# Development tooling

Last checked: 2026-08-15

## Rust migration commands

The staged Rust migration is tracked by
[`rust-migration-plan.md`](rust-migration-plan.md),
[`../migration/baseline.toml`](../migration/baseline.toml), and
[`../migration/parity.toml`](../migration/parity.toml). The host workspace pins
Rust 1.97.1; the isolated `thumbv5te-none-eabi` firmware workspace pins nightly
2026-08-14 and builds `core` from source.

- `cargo xtask check`: format, lint and test the stable host workspace, then
  format, lint, release-build, extract, pack, and exact-hash-check the ARMv5TE
  marker-first guard.
- `cargo xtask rust-guard`: build only the Rust firmware guard and place its
  verified code/container under `firmware/bk3635-rs/target/guard/`.
- `cargo xtask usb-probe`: rebuild the exact guard prefix and the isolated
  build-only endpoint-zero probe, then audit its prefix, symbols, MMIO loads,
  control flow, stack sizes, byte count, and SHA-256. It packs a hash-locked
  `DO_NOT_FLASH` container but does not access or flash the device.
- `cargo xtask postlink`: rerun the Rust guard ELF symbol audit.
- `cargo xtask all`: alias the complete Rust-only `check` gate.
- `cargo xtask disassemble-stock FIRMWARE START STOP arm|thumb`: hash-lock an
  external official v4.49 image and disassemble only the requested range.

The root [`rustfmt.toml`](../rustfmt.toml) is shared by every Rust workspace.
Workspace lint policy denies panic-prone conveniences (`panic!`, `unwrap`,
`expect`, and unchecked indexing), floating-point arithmetic, and accidental
`std` use where `core` or `alloc` is sufficient. Tests and audited fixed-layout
code use narrow `allow` attributes with reasons. Firmware additionally denies
integer division, unreachable placeholders, and unimplemented paths. Unsafe
code is warned rather than forbidden so a necessary startup or MMIO block must
be explicitly reviewed and annotated.

The post-link audit rejects empty or unresolved symbol tables and any linked
panic, unwind, allocation, or double-underscore compiler-runtime symbol. The
active gate audits the Rust-built marker-first guard and USB probe. Typed
binary verifiers retain the exact constraints and hashes of the earlier
recovery milestones.

The corrected 2026-08-15 build-only USB probe is 3,632 bytes with SHA-256
`cbe5bbbb119885f9d5b861b5548371a80672ada9b0ad9014069f12c8e41a9eca`.
Its first 420 bytes match the live-tested marker-first prefix; the 3,212-byte
experiment has 14 decoded, allowlisted MMIO loads, 22 defined symbols, no
undefined symbols, and a maximum recorded stack frame of 184 bytes. This is a
host audit result, not a hardware result.
The resulting 128,112-byte container has SHA-256
`3ce23e3b9af4a1e713bad622f56fc9055cb178ca1ec198c7556c1dee44169e5a`,
payload SHA-256
`6e14eedaa65930bca93fa60febd43f966f310743c9c4c7c79084865990192f7d`,
and payload CRC `2da6b921`. See
[`usb-recovery-probe.md`](usb-recovery-probe.md) for its staged hardware gate.

The protocol crate is dependency-free and `no_std`. It reproduces the existing
17-byte and 49-byte command reports, updater CRC, preparation report and B1
download blocks. All legacy packet cases are mapped in the parity manifest.
The host-only image crate ports header parsing, bounded CRC validation,
application packing and the v4.49 descriptor probe. Its only external direct
dependency is RustCrypto `sha2` 0.11.0 with default features disabled; it is
used solely for exact artifact identity checks.
The verifier crate keeps its ELF and checked address/branch primitives usable
without `std`; its default host feature adds complete artifact verifiers.
`cargo xtask check` compiles both configurations. Artifact tests compare typed
identities and generated outputs without writing to hardware. Reset and startup
trampolines share the same ARM executable-section verifier; both Rust builders
reproduce their recorded containers byte-for-byte.
The standalone recovery-stub Rust builder also reproduces its recorded
container byte-for-byte. Its verifier preserves the full legacy checks for the
startup transition, internal call graph, marker and flash MMIO sequences,
stock-derived delay, watchdog reset, ELF layout, erased padding, and exact
artifact identities.
The marker-first guard Rust builder reproduces the recorded 422-byte code and
container. Its storage-isolation audit scans every byte-aligned literal and
every halfword-aligned instruction, rejecting persistent-storage addresses,
out-of-range direct calls, indirect `BLX`, and software interrupts.
The recovery-carrier Rust builder reproduces the stock-derived injection,
dispatcher patches, metadata changes, and both header CRCs. Its verifier checks
the full MMIO literal table, stock unlock order, exact probe instructions,
unused gap, IRQ/FIQ preservation, and executable ELF layout.
The SDK-startup Rust verifier compares the rebuilt startup and IRQ/FIQ wrappers
directly with official v4.49, decodes reset and ARM/Thumb interrupt targets,
and validates the `.startup`, `.irq_wrapper`, and `.fiq_wrapper` ELF sections.
The Linux crate handles direct hidraw identity/descriptor access, sysfs parent
resolution, same-port re-enumeration, expected USB silence, pre-erase `B2/d2`
discovery, and the complete `B0`/`B1` transfer behind a fakeable transport
trait. The CLI crate makes exact artifact/action confirmation a typed gate.
These preserve every assertion from the former 88-test Python suite.

Build the host utility with `cargo build --release -p slimblade-cli`. Its
read-only identity command is `target/release/slimblade identify`; write
commands keep their confirmation at the command boundary. The same typed
transfer path supports every recorded hash-locked image and checks the expected
application version, resident-loader return, or guard USB silence afterward.
On 2026-08-15 the Rust identity path returned `047d:80d7`, `bcdDevice 0453`,
and the expected 170-byte descriptor from `/dev/slimblade-vendor`.

The 2026-08-15 hardware cutoff also passed: Rust flashed the exact marker-first
guard, verified 3,748 echoes and USB silence, recovered `25a7:fabe` after a
power cycle, restored the exact v4.53 image with another 3,748 verified echoes,
and rechecked the identity and descriptor. Physical ball, scroll, and button
operation were confirmed. The superseded Python implementation was then
removed.

## Stable device paths

[`udev/70-slimblade-research.rules`](../udev/70-slimblade-research.rules) now defines stable symlinks instead of requiring changing `hidrawN` numbers. The rule passes `udevadm verify` and is installed system-wide.

- `/dev/slimblade-vendor`: `047d:80d7`, USB interface `01`; verified as the 170-byte vendor/updater report-descriptor interface.
- `/dev/slimblade-loader`: any recorded loader identity (`25a7:fabe`, `3554:f600`, or `3554:f800`).

Live application validation passed on 2026-08-14: `/dev/slimblade-vendor` resolved to the current `/dev/hidraw4`, udev reported USB interface `01` and revision `0452`, and the utility read the expected 170-byte vendor descriptor. `/dev/slimblade-loader` is absent in normal application mode as intended; its rule awaits validation during the next loader transition.

The USB utility now defaults application commands to `/dev/slimblade-vendor`. Loader commands should name `/dev/slimblade-loader`; application flashing also scans that link and current `hidraw` nodes during its pre-erase retry window.

The normal mouse-report interface is USB interface `00` and should not receive updater commands. Current udev properties expose `ID_USB_INTERFACE_NUM=00` and `01`, so the application symlink distinguishes them without depending on enumeration order. An initial rule incorrectly combined USB-device and USB-interface `ATTRS` matches and did not create the link; the corrected rule uses the verified `ID_USB_INTERFACE_NUM=01` property.

A stable symlink does not by itself remove the resident loader's periodic disconnect/re-enumeration race. The flashing utility now searches the preferred path, `/dev/slimblade-loader`, and current `hidraw` nodes until it opens a recognized loader and receives `B2 → d2`. This retry is bounded and exists only before command `B0`. Once `B0` is attempted, any error stops without a blind retry because erase or partial transfer may already have started.
