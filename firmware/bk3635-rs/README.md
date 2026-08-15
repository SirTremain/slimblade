# BK3635 Rust firmware

This separate workspace pins nightly 2026-08-14 and builds `core` for
`thumbv5te-none-eabi`. The `slimblade-guard` executable reproduces the exact
marker-first hang guard that was tested on hardware.

The live-tested 420-byte recovery prefix remains reviewed ARM/Thumb assembly.
The first post-marker experiment is a Rust naked function containing the
two-byte hang. Linker assertions fix every recovery section address and size.
Run `cargo xtask rust-guard` at the repository root to build, extract, pack, and
hash-check the Rust artifact without Python or device access. Generated files
remain under `firmware/bk3635-rs/target/guard/`.
