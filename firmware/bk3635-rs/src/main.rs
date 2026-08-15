#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "this architecture entry module owns reviewed global assembly and exact linker symbols"
)]

use core::{
    arch::{global_asm, naked_asm},
    panic::PanicInfo,
};

global_asm!(include_str!("guard_prefix.S"), options(raw));

/// First Rust experimental payload entered only after the loader marker is complete.
#[unsafe(no_mangle)]
#[unsafe(naked)]
#[unsafe(link_section = ".text.rust_experiment")]
pub extern "C" fn rust_experiment() -> ! {
    naked_asm!("b .");
}

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "panic cannot unwind on the bare-metal target and must never modify recovery state"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
