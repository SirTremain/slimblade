#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "this entry module owns reviewed assembly linkage and the unique typed MMIO claim"
)]

use core::{arch::global_asm, panic::PanicInfo};
use slimblade_bk3635::{Mmio, PollOutcome, PollingUsbDevice};

global_asm!(
    include_str!("../../bk3635-rs/src/guard_prefix.S"),
    options(raw)
);

unsafe extern "C" {
    fn watchdog_reset() -> !;
}

/// Marker-first USB recovery experiment. It implements only enumeration and
/// the stock-compatible command that requests the resident loader.
#[unsafe(no_mangle)]
#[unsafe(link_section = ".text.rust_experiment")]
pub extern "C" fn rust_experiment() -> ! {
    // SAFETY: this is the sole hardware backend created by the single-threaded reset path.
    let registers = unsafe { Mmio::claim() };
    let mut usb = PollingUsbDevice::new(registers, 0x0454);
    usb.initialize();

    loop {
        if usb.poll() == PollOutcome::EnterLoader {
            // SAFETY: the marker prefix completed before this function, and this is the
            // live-tested watchdog reset routine from that same prefix.
            unsafe { watchdog_reset() }
        }
    }
}

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "panic must remain inert so a USB power cycle reaches the resident loader"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
