#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "reviewed FFI and volatile RAM access form the custom firmware boundary"
)]

use core::{arch::global_asm, panic::PanicInfo, ptr};

use slimblade_protocol::{
    NORMAL_REPORT_ID, SENSOR_STREAM_COMMAND, SENSOR_STREAM_VERSION, SensorStreamReport,
};

const VENDOR_ENDPOINT_READY: usize = 0x0040_0215;
const VENDOR_ENDPOINT_BLOCKED: usize = 0x0040_0213;
const VENDOR_ENDPOINT_ENABLED: usize = 0x0040_0217;
const VENDOR_RESPONSE_PENDING: usize = 0x0040_0374;
const VENDOR_RESPONSE_BUFFER: usize = 0x0040_15b0;
const USB_CONFIGURATION: usize = 0x0040_11cd;
const VENDOR_TRANSFER_LOW: usize = 0x0040_11de;
const VENDOR_TRANSFER_HIGH: usize = 0x0040_11df;

global_asm!(
    ".equ POST_INIT_HOOK_PROBE, 1",
    ".equ POST_INIT_EXPERIMENT_DISPATCH_GUARD, 1",
    ".equ CUSTOM_MAIN_STREAM_RUNTIME, 1",
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

        if read_byte(VENDOR_RESPONSE_PENDING) != 0 || !vendor_can_transmit() {
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
        };
        write_report(report);

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

fn vendor_can_transmit() -> bool {
    read_byte(VENDOR_ENDPOINT_READY) != 0
        && read_byte(VENDOR_ENDPOINT_BLOCKED) == 0
        && read_byte(USB_CONFIGURATION) != 0
        && read_byte(VENDOR_ENDPOINT_ENABLED) != 0
        && read_byte(VENDOR_TRANSFER_LOW) == 0
        && read_byte(VENDOR_TRANSFER_HIGH) == 0
}

fn write_report(report: SensorStreamReport) {
    let mut sum = 0_u8;
    write_checksummed_byte(0, NORMAL_REPORT_ID, &mut sum);
    write_checksummed_byte(1, SENSOR_STREAM_COMMAND, &mut sum);
    write_checksummed_byte(2, SENSOR_STREAM_VERSION, &mut sum);
    write_checksummed_byte(3, report.flags, &mut sum);
    write_halfword(4, report.sensor_a_x, &mut sum);
    write_halfword(6, report.sensor_a_y, &mut sum);
    write_halfword(8, report.sensor_b_x, &mut sum);
    write_halfword(10, report.sensor_b_y, &mut sum);
    write_checksummed_byte(12, report.buttons, &mut sum);
    write_checksummed_byte(13, report.sample_count, &mut sum);
    let [sequence_low, sequence_high] = report.sequence.to_le_bytes();
    write_checksummed_byte(14, sequence_low, &mut sum);
    write_checksummed_byte(15, sequence_high, &mut sum);
    write_byte(16, 0x55_u8.wrapping_sub(sum));
}

fn write_halfword(offset: usize, value: i16, sum: &mut u8) {
    let [low, high] = value.to_le_bytes();
    write_checksummed_byte(offset, low, sum);
    write_checksummed_byte(offset + 1, high, sum);
}

fn write_checksummed_byte(offset: usize, byte: u8, sum: &mut u8) {
    write_byte(offset, byte);
    *sum = sum.wrapping_add(byte);
}

fn write_byte(offset: usize, byte: u8) {
    // SAFETY: callers use only offsets within the stock 17-byte response buffer.
    unsafe {
        ptr::write_volatile(
            ptr::with_exposed_provenance_mut::<u8>(VENDOR_RESPONSE_BUFFER).add(offset),
            byte,
        );
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
