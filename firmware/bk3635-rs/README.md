# BK3635 Rust firmware

This separate workspace pins nightly 2026-08-14 and builds `core` for
`thumbv5te-none-eabi`. It currently contains only an inert `no_std` library used
to prove the toolchain; it does not produce a flashable image.

Byte-critical startup and recovery assembly will enter this workspace only
after the Rust host verifier reproduces every current artifact and safety check.
