#![no_main]
#![no_std]
#![allow(
    unsafe_code,
    reason = "reviewed FFI and volatile RAM access form the custom firmware boundary"
)]

use core::{arch::global_asm, panic::PanicInfo, ptr};

use slimblade_protocol::{
    NORMAL_REPORT_ID, SENSOR_STREAM_ACCUMULATOR_SATURATED, SENSOR_STREAM_COMMAND,
    SENSOR_STREAM_SAMPLE_COUNT_SATURATED, SENSOR_STREAM_VERSION, SensorStreamReport,
};

const VENDOR_ENDPOINT_READY: usize = 0x0040_0215;
const VENDOR_ENDPOINT_BLOCKED: usize = 0x0040_0213;
const VENDOR_ENDPOINT_ENABLED: usize = 0x0040_0217;
const VENDOR_RESPONSE_PENDING: usize = 0x0040_0374;
const SENSOR_SHADOW: usize = 0x0040_1360;
const VENDOR_RESPONSE_BUFFER: usize = 0x0040_15b0;
const USB_CONFIGURATION: usize = 0x0040_11cd;
const VENDOR_TRANSFER_LOW: usize = 0x0040_11de;
const VENDOR_TRANSFER_HIGH: usize = 0x0040_11df;

global_asm!(
    ".equ POST_INIT_HOOK_PROBE, 1",
    ".equ POST_INIT_EXPERIMENT_DISPATCH_GUARD, 1",
    ".equ CUSTOM_MAIN_STREAM_RUNTIME, 1",
    ".equ CUSTOM_MAIN_SENSOR_STREAM_PROBE, 1",
    ".equ SENSOR_SHADOW_ADDRESS, 0x00401360",
    include_str!("late_marker.S"),
    options(raw)
);

unsafe extern "C" {
    fn stock_vendor_dispatch();
    fn stock_vendor_transmit(report: *const u8);
    fn stock_sensor_service();
}

#[derive(Clone, Copy, Default)]
struct Accumulator {
    axes: [i16; 4],
    flags: u8,
    sample_count: u8,
    sequence: u16,
}

impl Accumulator {
    fn observe(&mut self, sample: [i16; 4]) {
        if sample == [0; 4] {
            return;
        }
        for (total, delta) in self.axes.iter_mut().zip(sample) {
            let (next, overflowed) = total.overflowing_add(delta);
            if overflowed {
                self.flags |= SENSOR_STREAM_ACCUMULATOR_SATURATED;
                *total = if delta.is_negative() {
                    i16::MIN
                } else {
                    i16::MAX
                };
            } else {
                *total = next;
            }
        }
        if let Some(next) = self.sample_count.checked_add(1) {
            self.sample_count = next;
        } else {
            self.flags |= SENSOR_STREAM_SAMPLE_COUNT_SATURATED;
        }
    }

    const fn report(self) -> SensorStreamReport {
        SensorStreamReport {
            flags: self.flags,
            sensor_a_x: self.axes[0],
            sensor_a_y: self.axes[1],
            sensor_b_x: self.axes[2],
            sensor_b_y: self.axes[3],
            buttons: 0,
            sample_count: self.sample_count,
            sequence: self.sequence,
        }
    }

    fn submitted(&mut self) {
        let sequence = self.sequence.wrapping_add(1);
        *self = Self {
            sequence,
            ..Self::default()
        };
    }
}

#[unsafe(no_mangle)]
#[unsafe(link_section = ".text.custom_runtime")]
pub extern "C" fn custom_runtime() -> ! {
    let mut accumulator = Accumulator::default();
    loop {
        // SAFETY: the locked stock dispatcher is live-proven at this exact Thumb address.
        unsafe { stock_vendor_dispatch() };

        clear_sensor_shadow();
        // SAFETY: the unchanged stock wired initializer has completed, and this exact
        // sensor service was live-proven before the stock pre-clear hook.
        unsafe { stock_sensor_service() };
        accumulator.observe(read_sensor_shadow());

        if read_byte(VENDOR_RESPONSE_PENDING) != 0 || !vendor_can_transmit() {
            continue;
        }

        write_report(accumulator.report());
        // SAFETY: the endpoint is ready, no recovery response is pending, and the
        // report points to the stock 17-byte vendor response buffer.
        unsafe { stock_vendor_transmit(ptr::with_exposed_provenance(VENDOR_RESPONSE_BUFFER)) };
        accumulator.submitted();
    }
}

fn clear_sensor_shadow() {
    // SAFETY: v4.70 live-proved this eight-byte inactive RAM shadow.
    unsafe {
        ptr::write_volatile(ptr::with_exposed_provenance_mut::<u32>(SENSOR_SHADOW), 0);
        ptr::write_volatile(
            ptr::with_exposed_provenance_mut::<u32>(SENSOR_SHADOW).add(1),
            0,
        );
    }
}

fn read_sensor_shadow() -> [i16; 4] {
    // SAFETY: the synchronous assembly hook has completed before these volatile reads.
    unsafe {
        let shadow = ptr::with_exposed_provenance::<i16>(SENSOR_SHADOW);
        [
            ptr::read_volatile(shadow),
            ptr::read_volatile(shadow.add(1)),
            ptr::read_volatile(shadow.add(2)),
            ptr::read_volatile(shadow.add(3)),
        ]
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

#[inline(never)]
#[unsafe(link_section = ".text.sensor_support")]
fn write_report(report: SensorStreamReport) {
    // SAFETY: every access is aligned and lies within the stock 17-byte response buffer.
    unsafe {
        let bytes = ptr::with_exposed_provenance_mut::<u8>(VENDOR_RESPONSE_BUFFER);
        ptr::write_volatile(bytes, NORMAL_REPORT_ID);
        ptr::write_volatile(bytes.add(1), SENSOR_STREAM_COMMAND);
        ptr::write_volatile(bytes.add(2), SENSOR_STREAM_VERSION);
        ptr::write_volatile(bytes.add(3), report.flags);
        let halfwords = ptr::with_exposed_provenance_mut::<i16>(VENDOR_RESPONSE_BUFFER);
        ptr::write_volatile(halfwords.add(2), report.sensor_a_x);
        ptr::write_volatile(halfwords.add(3), report.sensor_a_y);
        ptr::write_volatile(halfwords.add(4), report.sensor_b_x);
        ptr::write_volatile(halfwords.add(5), report.sensor_b_y);
        ptr::write_volatile(bytes.add(12), report.buttons);
        ptr::write_volatile(bytes.add(13), report.sample_count);
        ptr::write_volatile(
            ptr::with_exposed_provenance_mut::<u16>(VENDOR_RESPONSE_BUFFER).add(7),
            report.sequence,
        );
        let mut sum = 0_u8;
        let mut offset = 0;
        while offset < 16 {
            sum = sum.wrapping_add(ptr::read_volatile(bytes.add(offset)));
            offset += 1;
        }
        ptr::write_volatile(bytes.add(16), 0x55_u8.wrapping_sub(sum));
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
