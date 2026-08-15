#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "the firmware package includes reviewed ARM/Thumb startup assembly"
)]

use core::{arch::global_asm, panic::PanicInfo};

global_asm!(
    ".equ POST_INIT_HOOK_PROBE, 1",
    ".equ POST_INIT_STEADY_LOOP_HOOK_PROBE, 1",
    include_str!("late_marker.S"),
    options(raw)
);

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "the assembly-only probe has no Rust path that can panic"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
