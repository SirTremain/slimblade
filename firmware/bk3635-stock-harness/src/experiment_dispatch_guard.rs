#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "the firmware package includes reviewed ARM/Thumb startup assembly"
)]

use core::{arch::global_asm, panic::PanicInfo};

global_asm!(
    ".equ POST_INIT_HOOK_PROBE, 1",
    ".equ POST_INIT_EXPERIMENT_DISPATCH_GUARD, 1",
    include_str!("late_marker.S"),
    options(raw)
);

#[unsafe(no_mangle)]
#[unsafe(link_section = ".text.rust_probe")]
pub const extern "C" fn experiment_entry() {}

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "the returning probe has no Rust path that can panic"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
