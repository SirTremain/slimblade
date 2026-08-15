# Firmware layout

- [`bk3635-rs`](bk3635-rs) is the active Rust firmware workspace.
- `recovery_carrier`, `reset_trampoline`, `startup_trampoline`,
  `recovery_stub`, and `recovery_guard` retain readable milestone C/assembly
  and linker sources. They are not active build targets.

Run `cargo xtask all` from the repository root to build and verify the active
marker-first guard. Generated artifacts stay under ignored `target/` paths.
