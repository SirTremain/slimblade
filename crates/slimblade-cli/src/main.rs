use core::time::Duration;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use slimblade_cli::{
    FlashArtifact, PostFlashExpectation, active_loop_arm_response_is_success,
    dispatcher_return_arm_response_is_success, late_marker_response_is_success,
    post_init_arm_response_is_success, post_init_hook_state, rust_response_is_success,
    steady_loop_arm_response_is_success, wired_loop_arm_response_is_success,
};
use slimblade_linux::flash::{transfer_payload, wait_for_queried_loader};
use slimblade_linux::hidraw::Hidraw;
use slimblade_linux::sysfs::{
    HIDRAW_SYSFS_ROOT, observe_usb_silence, usb_parent_for_hidraw, wait_for_identity_at_path,
    wait_for_reenumeration,
};
use slimblade_protocol::{BOOT_IDENTITIES, KENSINGTON_WIRED_IDENTITY, NormalReport};

const DEFAULT_APPLICATION_DEVICE: &str = "/dev/slimblade-vendor";
const DEFAULT_LOADER_DEVICE: &str = "/dev/slimblade-loader";

#[derive(Debug)]
enum Command {
    Identify,
    EnterLoader {
        confirmed: bool,
    },
    SetLateMarker {
        confirmed: bool,
    },
    StartExperiment {
        confirmed: bool,
    },
    RunRustResponse {
        confirmed: bool,
    },
    RunPostInitHook {
        confirmed: bool,
    },
    QueryLoader,
    Flash {
        artifact: FlashArtifact,
        firmware: PathBuf,
        confirmation: String,
    },
}

#[derive(Debug)]
struct Arguments {
    device: PathBuf,
    timeout: Duration,
    command: Command,
}

const fn usage() -> &'static str {
    "usage:\n  slimblade [--device PATH] identify\n  slimblade [--device PATH] [--timeout-seconds N] enter-loader --confirm\n  slimblade [--device PATH] [--timeout-seconds N] set-late-marker --confirm\n  slimblade [--device PATH] [--timeout-seconds N] start-experiment --confirm\n  slimblade [--device PATH] [--timeout-seconds N] run-rust-response --confirm\n  slimblade [--device PATH] [--timeout-seconds N] run-post-init-hook --confirm\n  slimblade [--device PATH] [--timeout-seconds N] query-loader\n  slimblade [--device PATH] [--timeout-seconds N] FLASH_COMMAND --firmware PATH --confirm-sha256 HASH\n\nFLASH_COMMAND: restore-official-v449, flash-descriptor-probe, flash-recovery-carrier, flash-reset-trampoline, flash-recovery-stub, flash-startup-trampoline, flash-rust-guard, flash-usb-recovery-probe, flash-stock-harness, flash-late-marker-probe, flash-experiment-entry-probe, flash-rust-response-probe, flash-post-init-hook-probe, flash-wired-loop-hook-probe, flash-active-loop-hook-probe, flash-steady-loop-hook-probe, or flash-dispatcher-return-hook-probe"
}

fn flash_artifact_for_command(command: &str) -> Option<FlashArtifact> {
    match command {
        "restore-official-v449" => Some(FlashArtifact::OfficialV449),
        "flash-descriptor-probe" => Some(FlashArtifact::DescriptorProbe),
        "flash-recovery-carrier" => Some(FlashArtifact::RecoveryCarrier),
        "flash-reset-trampoline" => Some(FlashArtifact::ResetTrampoline),
        "flash-recovery-stub" => Some(FlashArtifact::RecoveryStub),
        "flash-startup-trampoline" => Some(FlashArtifact::StartupTrampoline),
        "flash-rust-guard" => Some(FlashArtifact::RecoveryGuard),
        "flash-usb-recovery-probe" => Some(FlashArtifact::UsbRecoveryProbe),
        "flash-stock-harness" => Some(FlashArtifact::StockHarness),
        "flash-late-marker-probe" => Some(FlashArtifact::LateMarkerProbe),
        "flash-experiment-entry-probe" => Some(FlashArtifact::ExperimentEntryProbe),
        "flash-rust-response-probe" => Some(FlashArtifact::RustResponseProbe),
        "flash-post-init-hook-probe" => Some(FlashArtifact::PostInitHookProbe),
        "flash-wired-loop-hook-probe" => Some(FlashArtifact::WiredLoopHookProbe),
        "flash-active-loop-hook-probe" => Some(FlashArtifact::ActiveLoopHookProbe),
        "flash-steady-loop-hook-probe" => Some(FlashArtifact::SteadyLoopHookProbe),
        "flash-dispatcher-return-hook-probe" => Some(FlashArtifact::DispatcherReturnHookProbe),
        _ => None,
    }
}

fn take_value(arguments: &[String], index: &mut usize, option: &str) -> Result<String, String> {
    *index = index
        .checked_add(1)
        .ok_or_else(|| "argument index overflow".to_owned())?;
    arguments
        .get(*index)
        .cloned()
        .ok_or_else(|| format!("{option} requires a value"))
}

fn parse_arguments() -> Result<Arguments, String> {
    let raw: Vec<String> = env::args().skip(1).collect();
    let mut device = None;
    let mut timeout = Duration::from_secs(3);
    let mut command_name = None;
    let mut confirmed = false;
    let mut firmware = None;
    let mut confirmation = None;
    let mut index = 0_usize;
    while index < raw.len() {
        let argument = raw
            .get(index)
            .ok_or_else(|| "argument index out of bounds".to_owned())?;
        match argument.as_str() {
            "--device" => device = Some(PathBuf::from(take_value(&raw, &mut index, argument)?)),
            "--timeout-seconds" => {
                let value = take_value(&raw, &mut index, argument)?;
                let seconds = value
                    .parse::<u64>()
                    .map_err(|error| format!("invalid timeout {value:?}: {error}"))?;
                timeout = Duration::from_secs(seconds);
            },
            "--confirm" => confirmed = true,
            "--firmware" => {
                firmware = Some(PathBuf::from(take_value(&raw, &mut index, argument)?));
            },
            "--confirm-sha256" => {
                confirmation = Some(take_value(&raw, &mut index, argument)?);
            },
            value if value.starts_with('-') => return Err(format!("unknown option {value:?}")),
            value if command_name.is_none() => command_name = Some(value.to_owned()),
            value => return Err(format!("unexpected argument {value:?}")),
        }
        index = index
            .checked_add(1)
            .ok_or_else(|| "argument index overflow".to_owned())?;
    }
    let command_name = command_name.ok_or_else(|| "missing command".to_owned())?;
    let command = match command_name.as_str() {
        "identify" => Command::Identify,
        "enter-loader" => Command::EnterLoader { confirmed },
        "set-late-marker" => Command::SetLateMarker { confirmed },
        "start-experiment" => Command::StartExperiment { confirmed },
        "run-rust-response" => Command::RunRustResponse { confirmed },
        "run-post-init-hook" => Command::RunPostInitHook { confirmed },
        "query-loader" => Command::QueryLoader,
        "restore-official-v449"
        | "flash-descriptor-probe"
        | "flash-recovery-carrier"
        | "flash-reset-trampoline"
        | "flash-recovery-stub"
        | "flash-startup-trampoline"
        | "flash-rust-guard"
        | "flash-usb-recovery-probe"
        | "flash-stock-harness"
        | "flash-late-marker-probe"
        | "flash-experiment-entry-probe"
        | "flash-rust-response-probe"
        | "flash-post-init-hook-probe"
        | "flash-wired-loop-hook-probe"
        | "flash-active-loop-hook-probe"
        | "flash-steady-loop-hook-probe"
        | "flash-dispatcher-return-hook-probe" => Command::Flash {
            artifact: flash_artifact_for_command(command_name.as_str())
                .ok_or_else(|| "unreachable flash command mapping".to_owned())?,
            firmware: firmware.ok_or_else(|| "flash command requires --firmware".to_owned())?,
            confirmation: confirmation
                .ok_or_else(|| "flash command requires --confirm-sha256".to_owned())?,
        },
        value => return Err(format!("unknown command {value:?}")),
    };
    let default_device = match command {
        Command::Identify
        | Command::EnterLoader { .. }
        | Command::SetLateMarker { .. }
        | Command::StartExperiment { .. }
        | Command::RunRustResponse { .. }
        | Command::RunPostInitHook { .. } => DEFAULT_APPLICATION_DEVICE,
        Command::QueryLoader | Command::Flash { .. } => DEFAULT_LOADER_DEVICE,
    };
    Ok(Arguments {
        device: device.unwrap_or_else(|| PathBuf::from(default_device)),
        timeout,
        command,
    })
}

fn identify(device: &Path) -> Result<(), String> {
    let hidraw = Hidraw::open_read_only(device)
        .map_err(|error| format!("could not open {}: {error}", device.display()))?;
    let (bus, identity) = hidraw
        .identity()
        .map_err(|error| format!("could not query HID identity: {error}"))?;
    let descriptor = hidraw
        .report_descriptor()
        .map_err(|error| format!("could not read HID report descriptor: {error}"))?;
    let parent = usb_parent_for_hidraw(device, Path::new(HIDRAW_SYSFS_ROOT))
        .map_err(|error| format!("could not resolve USB parent: {error}"))?
        .ok_or_else(|| "could not find USB parent".to_owned())?;
    if parent.identity != identity {
        return Err("HID identity and USB parent disagree".to_owned());
    }
    println!("device={}", device.display());
    println!("bus={bus}");
    println!(
        "identity={:04x}:{:04x}",
        identity.vendor_id, identity.product_id
    );
    println!("bcd_device={}", parent.bcd_device.as_deref().unwrap_or(""));
    println!("sysfs={}", parent.sysfs);
    println!("report_descriptor_bytes={}", descriptor.len());
    Ok(())
}

fn enter_loader(device: &Path, timeout: Duration, confirmed: bool) -> Result<(), String> {
    if !confirmed {
        return Err("refusing loader reset without --confirm".to_owned());
    }
    let parent = usb_parent_for_hidraw(device, Path::new(HIDRAW_SYSFS_ROOT))
        .map_err(|error| format!("could not resolve USB parent: {error}"))?
        .ok_or_else(|| "could not find USB parent".to_owned())?;
    let mut hidraw = Hidraw::open_read_write(device)
        .map_err(|error| format!("could not open {}: {error}", device.display()))?;
    let (_, identity) = hidraw
        .identity()
        .map_err(|error| format!("could not query HID identity: {error}"))?;
    if identity != KENSINGTON_WIRED_IDENTITY || parent.identity != identity {
        return Err(format!(
            "refusing reset for unexpected identity {:04x}:{:04x}",
            identity.vendor_id, identity.product_id
        ));
    }
    hidraw
        .write_report(NormalReport::reset_to_loader().as_bytes())
        .map_err(|error| format!("reset-to-loader report failed: {error}"))?;
    drop(hidraw);
    let loader = wait_for_identity_at_path(&parent.sysfs, &BOOT_IDENTITIES, timeout)
        .map_err(|error| format!("USB enumeration failed: {error}"))?
        .ok_or_else(|| "resident loader did not appear at the same USB path".to_owned())?;
    println!(
        "loader={:04x}:{:04x} sysfs={} devnum={}",
        loader.identity.vendor_id,
        loader.identity.product_id,
        loader.sysfs,
        loader.devnum.as_deref().unwrap_or("")
    );
    Ok(())
}

fn set_late_marker(device: &Path, timeout: Duration, confirmed: bool) -> Result<(), String> {
    if !confirmed {
        return Err("refusing persistent marker write without --confirm".to_owned());
    }
    let parent = usb_parent_for_hidraw(device, Path::new(HIDRAW_SYSFS_ROOT))
        .map_err(|error| format!("could not resolve USB parent: {error}"))?
        .ok_or_else(|| "could not find USB parent".to_owned())?;
    if parent.identity != KENSINGTON_WIRED_IDENTITY || parent.bcd_device.as_deref() != Some("0456")
    {
        return Err(format!(
            "refusing marker command for identity {:04x}:{:04x} bcdDevice={:?}; expected 047d:80d7/0456",
            parent.identity.vendor_id, parent.identity.product_id, parent.bcd_device
        ));
    }
    let mut hidraw = Hidraw::open_read_write(device)
        .map_err(|error| format!("could not open {}: {error}", device.display()))?;
    let (_, identity) = hidraw
        .identity()
        .map_err(|error| format!("could not query HID identity: {error}"))?;
    if identity != parent.identity {
        return Err("HID identity and USB parent disagree".to_owned());
    }
    hidraw
        .write_report(NormalReport::command(0x0e).as_bytes())
        .map_err(|error| format!("late-marker report failed: {error}"))?;
    let response = hidraw
        .read_normal_report(timeout.max(Duration::from_secs(3)))
        .map_err(|error| format!("late-marker response failed: {error}"))?
        .ok_or_else(|| "late-marker command did not return a vendor response".to_owned())?;
    if !late_marker_response_is_success(response) {
        return Err("late-marker command returned an unexpected response".to_owned());
    }
    println!(
        "late_marker=ack command=0e status=01 sysfs={}",
        parent.sysfs
    );
    Ok(())
}

fn start_experiment(device: &Path, timeout: Duration, confirmed: bool) -> Result<(), String> {
    if !confirmed {
        return Err("refusing marker-then-hang experiment without --confirm".to_owned());
    }
    let parent = usb_parent_for_hidraw(device, Path::new(HIDRAW_SYSFS_ROOT))
        .map_err(|error| format!("could not resolve USB parent: {error}"))?
        .ok_or_else(|| "could not find USB parent".to_owned())?;
    if parent.identity != KENSINGTON_WIRED_IDENTITY || parent.bcd_device.as_deref() != Some("0457")
    {
        return Err(format!(
            "refusing experiment command for identity {:04x}:{:04x} bcdDevice={:?}; expected 047d:80d7/0457",
            parent.identity.vendor_id, parent.identity.product_id, parent.bcd_device
        ));
    }
    let mut hidraw = Hidraw::open_read_write(device)
        .map_err(|error| format!("could not open {}: {error}", device.display()))?;
    let (_, identity) = hidraw
        .identity()
        .map_err(|error| format!("could not query HID identity: {error}"))?;
    if identity != parent.identity {
        return Err("HID identity and USB parent disagree".to_owned());
    }
    hidraw
        .write_report(NormalReport::command(0x0e).as_bytes())
        .map_err(|error| format!("experiment-entry report failed: {error}"))?;
    if hidraw
        .read_normal_report(timeout.max(Duration::from_secs(3)))
        .map_err(|error| format!("experiment-entry observation failed: {error}"))?
        .is_some()
    {
        return Err(
            "experiment returned an unexpected vendor response instead of hanging".to_owned(),
        );
    }
    println!(
        "experiment_entry=sent command=0e response=none expected=marker-then-hang sysfs={}",
        parent.sysfs
    );
    Ok(())
}

fn run_rust_response(device: &Path, timeout: Duration, confirmed: bool) -> Result<(), String> {
    if !confirmed {
        return Err("refusing marker-first Rust response probe without --confirm".to_owned());
    }
    let parent = usb_parent_for_hidraw(device, Path::new(HIDRAW_SYSFS_ROOT))
        .map_err(|error| format!("could not resolve USB parent: {error}"))?
        .ok_or_else(|| "could not find USB parent".to_owned())?;
    if parent.identity != KENSINGTON_WIRED_IDENTITY || parent.bcd_device.as_deref() != Some("0458")
    {
        return Err(format!(
            "refusing Rust response command for identity {:04x}:{:04x} bcdDevice={:?}; expected 047d:80d7/0458",
            parent.identity.vendor_id, parent.identity.product_id, parent.bcd_device
        ));
    }
    let mut hidraw = Hidraw::open_read_write(device)
        .map_err(|error| format!("could not open {}: {error}", device.display()))?;
    let (_, identity) = hidraw
        .identity()
        .map_err(|error| format!("could not query HID identity: {error}"))?;
    if identity != parent.identity {
        return Err("HID identity and USB parent disagree".to_owned());
    }
    hidraw
        .write_report(NormalReport::command(0x0e).as_bytes())
        .map_err(|error| format!("Rust response report failed: {error}"))?;
    let response = hidraw
        .read_normal_report(timeout.max(Duration::from_secs(3)))
        .map_err(|error| format!("Rust response read failed: {error}"))?
        .ok_or_else(|| "Rust response probe did not return a vendor response".to_owned())?;
    if !rust_response_is_success(response) {
        return Err("Rust response probe returned an unexpected signature or status".to_owned());
    }
    println!(
        "rust_response=ack command=0e status=01 signature=58 sysfs={}",
        parent.sysfs
    );
    Ok(())
}

fn exchange_vendor_command(
    hidraw: &mut Hidraw,
    command: u8,
    timeout: Duration,
) -> Result<NormalReport, String> {
    hidraw
        .write_report(NormalReport::command(command).as_bytes())
        .map_err(|error| format!("vendor command {command:#04x} failed: {error}"))?;
    hidraw
        .read_normal_report(timeout.max(Duration::from_secs(3)))
        .map_err(|error| format!("vendor response {command:#04x} failed: {error}"))?
        .ok_or_else(|| format!("vendor command {command:#04x} returned no response"))
}

fn run_post_init_hook(device: &Path, timeout: Duration, confirmed: bool) -> Result<(), String> {
    if !confirmed {
        return Err("refusing persistent-marker hook probe without --confirm".to_owned());
    }
    let parent = usb_parent_for_hidraw(device, Path::new(HIDRAW_SYSFS_ROOT))
        .map_err(|error| format!("could not resolve USB parent: {error}"))?
        .ok_or_else(|| "could not find USB parent".to_owned())?;
    if parent.identity != KENSINGTON_WIRED_IDENTITY {
        return Err(format!(
            "refusing post-init hook command for identity {:04x}:{:04x} bcdDevice={:?}; expected 047d:80d7",
            parent.identity.vendor_id, parent.identity.product_id, parent.bcd_device
        ));
    }
    let (expected_state, expected_signature, armed_state) = match parent.bcd_device.as_deref() {
        Some("0459") => (2_u8, 0xa3_u8, 3_u8),
        Some("0460") => (0_u8, 0xa5_u8, 5_u8),
        Some("0461") => (0_u8, 0xa6_u8, 5_u8),
        Some("0462") => (0_u8, 0xa7_u8, 5_u8),
        Some("0463") => (0_u8, 0xa8_u8, 5_u8),
        _ => {
            return Err(format!(
                "refusing post-init hook command for bcdDevice={:?}; expected 0459, 0460, 0461, 0462, or 0463",
                parent.bcd_device
            ));
        },
    };
    let mut hidraw = Hidraw::open_read_write(device)
        .map_err(|error| format!("could not open {}: {error}", device.display()))?;
    let (_, identity) = hidraw
        .identity()
        .map_err(|error| format!("could not query HID identity: {error}"))?;
    if identity != parent.identity {
        return Err("HID identity and USB parent disagree".to_owned());
    }

    let initial = exchange_vendor_command(&mut hidraw, 0x0f, timeout)?;
    let initial_state = post_init_hook_state(initial);
    if initial_state != Some(expected_state) {
        return Err(format!(
            "post-init hook preflight reported mode {initial_state:?}, expected Some({expected_state})"
        ));
    }
    let armed = exchange_vendor_command(&mut hidraw, 0x0e, timeout)?;
    let arm_succeeded = match expected_signature {
        0xa3 => post_init_arm_response_is_success(armed),
        0xa5 => wired_loop_arm_response_is_success(armed),
        0xa6 => active_loop_arm_response_is_success(armed),
        0xa7 => steady_loop_arm_response_is_success(armed),
        0xa8 => dispatcher_return_arm_response_is_success(armed),
        _ => false,
    };
    if !arm_succeeded {
        return Err(format!(
            "marker command did not return status 01 and signature {expected_signature:02x}"
        ));
    }

    for attempt in 1_u8..=8_u8 {
        let response = exchange_vendor_command(&mut hidraw, 0x0f, timeout)?;
        match post_init_hook_state(response) {
            Some(state) if state == expected_state => {
                println!(
                    "post_init_hook=pass initial={expected_state:02x} arm_signature={expected_signature:02x} final={state:02x} attempts={attempt} sysfs={}",
                    parent.sysfs
                );
                return Ok(());
            },
            Some(state) if state == armed_state => {},
            Some(state) => {
                return Err(format!(
                    "post-init hook returned unexpected mode {state:#04x}"
                ));
            },
            None => return Err("post-init hook state response was malformed".to_owned()),
        }
    }
    Err("post-init hook remained armed after eight queries".to_owned())
}

fn query_loader(device: &Path, timeout: Duration) -> Result<(), String> {
    let loader = wait_for_queried_loader(device, timeout.max(Duration::from_secs(8)))
        .map_err(|error| error.to_string())?;
    println!(
        "loader=d2 identity={:04x}:{:04x} device={} sysfs={}",
        loader.usb_parent.identity.vendor_id,
        loader.usb_parent.identity.product_id,
        loader.path.display(),
        loader.usb_parent.sysfs
    );
    Ok(())
}

fn flash_artifact(
    device: &Path,
    timeout: Duration,
    artifact: FlashArtifact,
    firmware: &Path,
    confirmation: &str,
) -> Result<(), String> {
    if !artifact.confirmation_matches(confirmation) {
        return Err(format!(
            "refusing flash: --confirm-sha256 must equal {}",
            artifact.confirmation_sha256()
        ));
    }
    let image = fs::read(firmware)
        .map_err(|error| format!("could not read {}: {error}", firmware.display()))?;
    let payload = artifact
        .identity()
        .validate(&image)
        .map_err(|error| format!("refusing flash: {error}"))?;
    let mut loader = wait_for_queried_loader(device, timeout.max(Duration::from_secs(8)))
        .map_err(|error| format!("no erase was attempted: {error}"))?;
    println!(
        "loader query: d2; image={} payload={} bytes crc={:08x}",
        artifact.confirmation_sha256(),
        payload.len(),
        artifact.identity().payload_crc
    );
    let previous = loader.usb_parent.clone();
    let mut next_percent = 5_usize;
    let blocks = transfer_payload(loader.transport_mut(), payload, timeout, |done, total| {
        let percent = done.saturating_mul(100).checked_div(total).unwrap_or(0);
        if percent >= next_percent || done == total {
            println!("write/verify: {percent}% ({done}/{total})");
            next_percent = percent.saturating_add(5);
        }
    })
    .map_err(|error| format!("flash failed after erase boundary: {error}"))?;
    drop(loader);
    match artifact.post_flash_expectation() {
        PostFlashExpectation::Application { bcd_device } => {
            let application = wait_for_reenumeration(
                &previous,
                &[KENSINGTON_WIRED_IDENTITY],
                Duration::from_secs(20),
            )
            .map_err(|error| format!("post-flash USB observation failed: {error}"))?
            .ok_or_else(|| {
                "final block echoed, but the application did not return at the same USB path"
                    .to_owned()
            })?;
            if application.bcd_device.as_deref() != Some(bcd_device) {
                return Err(format!(
                    "application returned with bcdDevice={:?}, expected {bcd_device}",
                    application.bcd_device
                ));
            }
            println!(
                "application={:04x}:{:04x} bcdDevice={bcd_device} sysfs={}",
                application.identity.vendor_id, application.identity.product_id, application.sysfs
            );
            println!("flash complete: {blocks} blocks echoed");
        },
        PostFlashExpectation::ResidentLoader => {
            let resident =
                wait_for_reenumeration(&previous, &BOOT_IDENTITIES, Duration::from_secs(20))
                    .map_err(|error| format!("post-flash USB observation failed: {error}"))?
                    .ok_or_else(|| {
                        "final block echoed, but a new resident-loader enumeration did not appear"
                            .to_owned()
                    })?;
            println!(
                "resident_loader={:04x}:{:04x} sysfs={}",
                resident.identity.vendor_id, resident.identity.product_id, resident.sysfs
            );
            println!("flash complete: {blocks} blocks echoed");
        },
        PostFlashExpectation::UsbSilence => {
            if !observe_usb_silence(&previous, timeout.max(Duration::from_secs(5)))
                .map_err(|error| format!("post-flash USB observation failed: {error}"))?
            {
                return Err(
                    "final block echoed, but expected marker-first USB silence was not observed"
                        .to_owned(),
                );
            }
            println!("guard complete: {blocks} blocks echoed; expected USB silence observed");
        },
    }
    Ok(())
}

fn run() -> Result<(), String> {
    let arguments = parse_arguments()?;
    match arguments.command {
        Command::Identify => identify(&arguments.device),
        Command::EnterLoader { confirmed } => {
            enter_loader(&arguments.device, arguments.timeout, confirmed)
        },
        Command::SetLateMarker { confirmed } => {
            set_late_marker(&arguments.device, arguments.timeout, confirmed)
        },
        Command::StartExperiment { confirmed } => {
            start_experiment(&arguments.device, arguments.timeout, confirmed)
        },
        Command::RunRustResponse { confirmed } => {
            run_rust_response(&arguments.device, arguments.timeout, confirmed)
        },
        Command::RunPostInitHook { confirmed } => {
            run_post_init_hook(&arguments.device, arguments.timeout, confirmed)
        },
        Command::QueryLoader => query_loader(&arguments.device, arguments.timeout),
        Command::Flash {
            artifact,
            firmware,
            confirmation,
        } => flash_artifact(
            &arguments.device,
            arguments.timeout,
            artifact,
            &firmware,
            &confirmation,
        ),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}\n{}", usage());
            ExitCode::from(2)
        },
    }
}
