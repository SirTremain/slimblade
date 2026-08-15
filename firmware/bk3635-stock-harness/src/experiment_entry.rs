#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "the firmware package consists solely of reviewed ARM/Thumb startup assembly"
)]

use core::{arch::global_asm, panic::PanicInfo};

global_asm!(
    ".equ EXPERIMENT_ENTRY_HANG, 1",
    include_str!("late_marker.S"),
    options(raw)
);

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "no Rust path calls panic; an inert handler prevents unexpected reset behavior"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
