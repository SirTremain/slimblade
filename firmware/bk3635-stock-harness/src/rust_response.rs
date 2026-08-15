#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "the firmware package includes reviewed ARM/Thumb startup assembly"
)]

use core::{arch::global_asm, panic::PanicInfo};

global_asm!(
    ".equ RUST_RESPONSE_PROBE, 1",
    include_str!("late_marker.S"),
    options(raw)
);

#[unsafe(no_mangle)]
#[unsafe(link_section = ".text.rust_probe")]
pub const extern "C" fn rust_probe_value() -> u32 {
    0x58
}

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "no Rust path calls panic; an inert handler prevents unexpected reset behavior"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
