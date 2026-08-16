#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "reviewed FFI and volatile RAM access form the custom firmware boundary"
)]

use core::{arch::global_asm, panic::PanicInfo, ptr};

use slimblade_protocol::SensorStreamReport;

const VENDOR_ENDPOINT_READY: usize = 0x0040_0215;
const VENDOR_RESPONSE_PENDING: usize = 0x0040_0374;
const VENDOR_RESPONSE_BUFFER: usize = 0x0040_15b0;

global_asm!(
    ".equ POST_INIT_HOOK_PROBE, 1",
    ".equ POST_INIT_EXPERIMENT_DISPATCH_GUARD, 1",
    ".equ CUSTOM_MAIN_STREAM_TRANSPORT_PROBE, 1",
    include_str!("late_marker.S"),
    options(raw)
);

unsafe extern "C" {
    fn stock_vendor_dispatch();
    fn stock_vendor_transmit(report: *const u8);
}

#[unsafe(no_mangle)]
#[unsafe(link_section = ".text.custom_runtime")]
pub extern "C" fn custom_runtime() -> ! {
    let mut sequence = 0_u16;
    loop {
        // SAFETY: the locked stock dispatcher is live-proven at this exact Thumb address.
        unsafe { stock_vendor_dispatch() };

        if read_byte(VENDOR_RESPONSE_PENDING) != 0 || read_byte(VENDOR_ENDPOINT_READY) == 0 {
            continue;
        }

        let report = SensorStreamReport {
            flags: 0,
            sensor_a_x: 0,
            sensor_a_y: 0,
            sensor_b_x: 0,
            sensor_b_y: 0,
            buttons: 0,
            sample_count: 0,
            sequence,
        }
        .encode();
        write_report(report.as_bytes());

        // SAFETY: the endpoint is ready, no recovery response is pending, and the
        // report points to the stock 17-byte vendor response buffer.
        unsafe { stock_vendor_transmit(ptr::with_exposed_provenance(VENDOR_RESPONSE_BUFFER)) };
        sequence = sequence.wrapping_add(1);
    }
}

fn read_byte(address: usize) -> u8 {
    // SAFETY: these byte-wide stock USB state locations are locked by the image audit.
    unsafe { ptr::read_volatile(ptr::with_exposed_provenance(address)) }
}

fn write_report(report: &[u8; 17]) {
    for (offset, byte) in report.iter().copied().enumerate() {
        // SAFETY: every offset is within the stock 17-byte vendor response buffer.
        unsafe {
            ptr::write_volatile(
                ptr::with_exposed_provenance_mut::<u8>(VENDOR_RESPONSE_BUFFER).add(offset),
                byte,
            );
        }
    }
}

#[panic_handler]
#[allow(
    clippy::empty_loop,
    reason = "panic cannot unwind on the firmware target; recovery remains power-cycle driven"
)]
const fn panic(_information: &PanicInfo<'_>) -> ! {
    loop {}
}
