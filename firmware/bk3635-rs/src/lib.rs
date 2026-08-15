#![no_std]
#![forbid(unsafe_code)]

/// Compile-time marker for the initial Rust toolchain smoke test.
pub const TARGET_ARCHITECTURE: &str = "thumbv5te-none-eabi";
