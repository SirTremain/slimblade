# SlimBlade Pro research

Compact notes on the Kensington SlimBlade Pro sensor and firmware interface.

- [Firmware research](docs/firmware-research.md)
- [Custom-firmware and recovery gates](docs/custom-firmware-feasibility.md)
- [Recovery-stub path](docs/recovery-stub.md)
- [Marker-first recovery guard](docs/recovery-guard.md)
- [Stock recovery carrier](docs/recovery-carrier.md)
- [Reset trampoline](docs/reset-trampoline.md)
- [Startup trampoline](docs/startup-trampoline.md)
- [BK3633 SDK comparison](docs/bk3633-sdk-comparison.md)
- [Vendored BK3633 SDK](vendor/bk3633_sdk/README.md)
- [BK3635 wired port starting point](vendor/bk3633_sdk/SDK/projects/slimblade_wired/README.md)
- [Development tooling](docs/development-tooling.md)
- [Custom firmware architecture](docs/development-architecture.md)
- [Post-initialization recovery marker](docs/post-init-marker.md)
- [Rust migration plan](docs/rust-migration-plan.md)
- [Board observations](docs/board-observations.md)

Active development support:

- [`crates/slimblade-cli`](crates/slimblade-cli): guarded Linux HID inspection,
  loader control, and exact-hash flashing.
- [`crates/slimblade-protocol`](crates/slimblade-protocol): `no_std` wire
  reports, checksums, CRC, and fixed-size packet types.
- [`crates/slimblade-image`](crates/slimblade-image): firmware containers and
  recorded artifact identities.
- [`crates/slimblade-verify`](crates/slimblade-verify): ELF, ARM/Thumb, artifact,
  and storage-isolation checks.
- [`firmware/bk3635-rs`](firmware/bk3635-rs): Rust marker-first firmware.
- [`udev/70-slimblade-research.rules`](udev/70-slimblade-research.rules):
  scoped permissions and stable HID paths.

Run `cargo xtask all` for the complete non-writing build and verification gate.
The retained C/assembly probes and vendored BK3633 SDK are research references,
not part of the active build.
