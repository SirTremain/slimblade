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
  format, lint and release-build the inert ARMv5TE firmware scaffold.
- `cargo xtask legacy`: run all 88 Python tests and every existing firmware
  preflight, then audit every generated ELF symbol table.
- `cargo xtask postlink`: rerun only the ELF symbol audit after artifacts have
  been built.
- `cargo xtask all`: require both gates.

The root [`rustfmt.toml`](../rustfmt.toml) is shared by every Rust workspace.
Workspace lint policy denies panic-prone conveniences (`panic!`, `unwrap`,
`expect`, and unchecked indexing), floating-point arithmetic, and accidental
`std` use where `core` or `alloc` is sufficient. Tests and audited fixed-layout
code use narrow `allow` attributes with reasons. Firmware additionally denies
integer division, unreachable placeholders, and unimplemented paths. Unsafe
code is warned rather than forbidden so a necessary startup or MMIO block must
be explicitly reviewed and annotated.

The post-link audit rejects empty or unresolved symbol tables and any linked
panic, unwind, allocation, or double-underscore compiler-runtime symbol. It
currently covers the SDK startup reference, carrier, both trampolines, and
standalone recovery stub. The marker-first guard has no ELF and remains covered
by its binary call-target and storage-isolation verifier. The Rust firmware
workspace still produces only an inert `rlib`; its final executable must be
added to the audited ELF list as soon as that target exists.

The protocol crate is dependency-free and `no_std`. It reproduces the existing
17-byte and 49-byte command reports, updater CRC, preparation report and B1
download blocks. Eight legacy packet cases are mapped in the parity manifest.
The host-only image crate ports header parsing, bounded CRC validation,
application packing and the v4.49 descriptor probe. Its only external direct
dependency is RustCrypto `sha2` 0.11.0 with default features disabled; it is
used solely for exact artifact identity checks.
The verifier crate keeps its ELF and checked address/branch primitives usable
without `std`; its default host feature adds complete artifact verifiers.
`cargo xtask check` compiles both configurations. Artifact tests compare typed
identities and generated outputs without writing to hardware.

## Stable device paths

[`udev/70-slimblade-research.rules`](../udev/70-slimblade-research.rules) now defines stable symlinks instead of requiring changing `hidrawN` numbers. The rule passes `udevadm verify` and is installed system-wide.

- `/dev/slimblade-vendor`: `047d:80d7`, USB interface `01`; verified as the 170-byte vendor/updater report-descriptor interface.
- `/dev/slimblade-loader`: any recorded loader identity (`25a7:fabe`, `3554:f600`, or `3554:f800`).

Live application validation passed on 2026-08-14: `/dev/slimblade-vendor` resolved to the current `/dev/hidraw4`, udev reported USB interface `01` and revision `0452`, and the utility read the expected 170-byte vendor descriptor. `/dev/slimblade-loader` is absent in normal application mode as intended; its rule awaits validation during the next loader transition.

The USB utility now defaults application commands to `/dev/slimblade-vendor`. Loader commands should name `/dev/slimblade-loader`; application flashing also scans that link and current `hidraw` nodes during its pre-erase retry window.

The normal mouse-report interface is USB interface `00` and should not receive updater commands. Current udev properties expose `ID_USB_INTERFACE_NUM=00` and `01`, so the application symlink distinguishes them without depending on enumeration order. An initial rule incorrectly combined USB-device and USB-interface `ATTRS` matches and did not create the link; the corrected rule uses the verified `ID_USB_INTERFACE_NUM=01` property.

A stable symlink does not by itself remove the resident loader's periodic disconnect/re-enumeration race. The flashing utility now searches the preferred path, `/dev/slimblade-loader`, and current `hidraw` nodes until it opens a recognized loader and receives `B2 → d2`. This retry is bounded and exists only before command `B0`. Once `B0` is attempted, any error stops without a blind retry because erase or partial transfer may already have started.
