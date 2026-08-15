use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{self, Command, ExitCode};
use std::time::{SystemTime, UNIX_EPOCH};

use slimblade_image::{
    OFFICIAL_V449, RECOVERY_GUARD, RECOVERY_GUARD_ARTIFACT, USB_RECOVERY_PROBE,
    USB_RECOVERY_PROBE_ARTIFACT, sha256,
};
use slimblade_protocol::updater_crc32;
use slimblade_verify::post_link::audit_nm_outputs;
use slimblade_verify::usb_probe::{EXPERIMENT_ADDRESS, audit_code};

const FIRMWARE_TOOLCHAIN: &str = "+nightly-2026-08-14";
const POST_LINK_ELFS: &[&str] =
    &["firmware/bk3635-rs/target/thumbv5te-none-eabi/release/slimblade-guard"];
const USB_PROBE_BINARY: &str = "slimblade-usb-recovery-probe";
const USB_PROBE_MAX_STACK_BYTES: usize = 256;
const USB_PROBE_CODE_ADDRESS: u32 = 0x0000_2020;
const SYSTEM_MMIO_START: u32 = 0x0080_0000;
const SYSTEM_MMIO_END: u32 = 0x0081_0000;
const ALLOWED_USB_PROBE_MMIO: &[u32] = &[
    0x0080_0020,
    0x0080_0040,
    0x0080_0044,
    0x0080_4000,
    0x0080_4011,
    0x0080_4020,
    0x0080_4080,
    0x0080_6520,
    0x0080_6524,
];

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn run(root: &Path, program: &str, arguments: &[&str]) -> Result<(), String> {
    eprintln!("+ {program} {}", arguments.join(" "));
    let status = Command::new(program)
        .args(arguments)
        .current_dir(root)
        .status()
        .map_err(|error| format!("could not run {program}: {error}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("{program} exited with {status}"))
    }
}

fn host_checks(root: &Path) -> Result<(), String> {
    run(root, "cargo", &["fmt", "--all", "--check"])?;
    run(
        root,
        "cargo",
        &[
            "clippy",
            "--workspace",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
    )?;
    run(root, "cargo", &["test", "--workspace"])?;
    run(
        root,
        "cargo",
        &[
            "check",
            "--package",
            "slimblade-verify",
            "--no-default-features",
        ],
    )?;

    let firmware = root.join("firmware/bk3635-rs");
    run(&firmware, "cargo", &[FIRMWARE_TOOLCHAIN, "fmt", "--check"])?;
    run(
        &firmware,
        "cargo",
        &[
            FIRMWARE_TOOLCHAIN,
            "clippy",
            "--lib",
            "--bin",
            "slimblade-guard",
            "--",
            "-D",
            "warnings",
        ],
    )?;
    run(
        &firmware,
        "cargo",
        &[FIRMWARE_TOOLCHAIN, "build", "--release"],
    )?;
    build_rust_guard(root)?;
    post_link_checks(root)?;
    build_usb_probe(root)
}

fn build_rust_guard(root: &Path) -> Result<(), String> {
    let firmware = root.join("firmware/bk3635-rs");
    run(
        &firmware,
        "cargo",
        &[
            FIRMWARE_TOOLCHAIN,
            "build",
            "--release",
            "--bin",
            "slimblade-guard",
        ],
    )?;

    let elf = firmware.join("target/thumbv5te-none-eabi/release/slimblade-guard");
    let artifact_dir = firmware.join("target/guard");
    fs::create_dir_all(&artifact_dir)
        .map_err(|error| format!("could not create {}: {error}", artifact_dir.display()))?;
    let code_path = artifact_dir.join("DO_NOT_FLASH-rust-marker-first-guard.code.bin");
    let container_path = artifact_dir.join("DO_NOT_FLASH-rust-marker-first-guard.container.bin");
    eprintln!(
        "+ llvm-objcopy -O binary {} {}",
        elf.display(),
        code_path.display()
    );
    let status = Command::new("llvm-objcopy")
        .args(["-O", "binary"])
        .arg(&elf)
        .arg(&code_path)
        .current_dir(root)
        .status()
        .map_err(|error| format!("could not run llvm-objcopy: {error}"))?;
    if !status.success() {
        return Err(format!("llvm-objcopy exited with {status}"));
    }

    let code = fs::read(&code_path)
        .map_err(|error| format!("could not read {}: {error}", code_path.display()))?;
    if !RECOVERY_GUARD_ARTIFACT.code_matches(&code) {
        return Err("Rust guard code does not match the live-tested 422-byte identity".to_owned());
    }
    let container = slimblade_verify::recovery_stub::build(&code)
        .map_err(|error| format!("could not pack Rust guard: {error}"))?;
    RECOVERY_GUARD
        .validate(&container)
        .map_err(|error| format!("Rust guard container identity failed: {error}"))?;
    fs::write(&container_path, &container)
        .map_err(|error| format!("could not write {}: {error}", container_path.display()))?;
    eprintln!(
        "Rust guard PASS: {} code bytes, {} container bytes",
        code.len(),
        container.len()
    );
    Ok(())
}

fn llvm_nm(root: &Path, elf: &str, mode: &str) -> Result<String, String> {
    eprintln!("+ llvm-nm {mode} --demangle {elf}");
    let output = Command::new("llvm-nm")
        .args([mode, "--demangle", elf])
        .current_dir(root)
        .output()
        .map_err(|error| format!("could not inspect {elf}: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "llvm-nm failed for {elf}: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    String::from_utf8(output.stdout)
        .map_err(|error| format!("llvm-nm returned non-UTF-8 output for {elf}: {error}"))
}

fn post_link_checks(root: &Path) -> Result<(), String> {
    for elf in POST_LINK_ELFS {
        let defined = llvm_nm(root, elf, "--defined-only")?;
        let undefined = llvm_nm(root, elf, "--undefined-only")?;
        let report = audit_nm_outputs(&defined, &undefined)
            .map_err(|error| format!("post-link audit failed for {elf}: {error}"))?;
        eprintln!(
            "post-link PASS: {elf} ({} defined symbols)",
            report.defined_symbols
        );
    }
    Ok(())
}

fn command_output(directory: &Path, program: &str, arguments: &[String]) -> Result<String, String> {
    eprintln!("+ {program} {}", arguments.join(" "));
    let output = Command::new(program)
        .args(arguments)
        .current_dir(directory)
        .output()
        .map_err(|error| format!("could not run {program}: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "{program} failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    String::from_utf8(output.stdout)
        .map_err(|error| format!("{program} returned non-UTF-8 output: {error}"))
}

fn audit_probe_disassembly(
    disassembly: &str,
    code: &[u8],
    executable_end: u32,
) -> Result<usize, String> {
    const FORBIDDEN_MNEMONICS: &[&str] = &["svc", "swi", "udf"];

    let mut mmio_literals = 0_usize;
    let mut has_usb_clock_control = false;
    let mut has_usb_controller = false;
    let mut has_usb_platform_control = false;
    for line in disassembly.lines() {
        let mut columns = line.split_whitespace();
        let Some(address) = columns.next() else {
            continue;
        };
        if !address.ends_with(':') {
            continue;
        }
        let Some(_encoding) = columns.next() else {
            continue;
        };
        let Some(mnemonic) = columns.next() else {
            continue;
        };
        let operands = columns.collect::<Vec<_>>().join(" ");
        let writes_pc = (mnemonic == "mov" || mnemonic == "add" || mnemonic == "ldr")
            && operands
                .split(',')
                .next()
                .is_some_and(|operand| operand.trim() == "pc");
        let indirect_blx = mnemonic == "blx" && operands.trim_start().starts_with('r');
        let non_return_bx = mnemonic == "bx" && operands.trim() != "lr";
        if FORBIDDEN_MNEMONICS.contains(&mnemonic) || writes_pc || indirect_blx || non_return_bx {
            return Err(format!("forbidden experiment instruction: {line}"));
        }

        let direct_branch = mnemonic == "bl"
            || (mnemonic.starts_with('b')
                && mnemonic != "bic"
                && mnemonic != "bics"
                && mnemonic != "blx"
                && mnemonic != "bx");
        if direct_branch {
            let target = operands
                .split_whitespace()
                .next()
                .ok_or_else(|| format!("branch has no decoded target: {line}"))?;
            let target = u32::try_from(parse_address(target)?).map_err(|error| {
                format!("branch target does not fit the BK3635 address space: {error}")
            })?;
            let internal = (EXPERIMENT_ADDRESS..executable_end).contains(&target);
            let reviewed_reset = mnemonic == "bl" && target == 0x0000_20fc;
            if !internal && !reviewed_reset {
                return Err(format!("branch escapes reviewed experiment code: {line}"));
            }
        }

        if mnemonic != "ldr" || !operands.contains("[pc") {
            continue;
        }
        let target = operands
            .split_whitespace()
            .skip_while(|field| *field != "@")
            .nth(1)
            .ok_or_else(|| format!("PC-relative load has no decoded target: {line}"))?;
        let target = u32::try_from(parse_address(target)?).map_err(|error| {
            format!("literal target does not fit the BK3635 address space: {error}")
        })?;
        let offset = target
            .checked_sub(USB_PROBE_CODE_ADDRESS)
            .ok_or_else(|| format!("literal target precedes probe code: {line}"))?;
        let offset = usize::try_from(offset)
            .map_err(|error| format!("literal offset does not fit usize: {error}"))?;
        let end = offset
            .checked_add(4)
            .ok_or_else(|| "literal offset overflow".to_owned())?;
        let bytes = code
            .get(offset..end)
            .and_then(|literal| <[u8; 4]>::try_from(literal).ok())
            .ok_or_else(|| format!("literal target lies outside extracted code: {line}"))?;
        let value = u32::from_le_bytes(bytes);
        if (SYSTEM_MMIO_START..SYSTEM_MMIO_END).contains(&value) {
            if !ALLOWED_USB_PROBE_MMIO.contains(&value) {
                return Err(format!(
                    "unreviewed MMIO literal {value:#010x} loaded by: {line}"
                ));
            }
            mmio_literals = mmio_literals.saturating_add(1);
            has_usb_clock_control |= value == 0x0080_0020;
            has_usb_controller |= value == 0x0080_4000;
            has_usb_platform_control |= value == 0x0080_6520;
        }
    }
    if !has_usb_clock_control {
        return Err("experiment does not load the stock USB clock-control address".to_owned());
    }
    if !has_usb_controller {
        return Err("experiment does not load the reviewed USB base address".to_owned());
    }
    if !has_usb_platform_control {
        return Err("experiment does not load the stock USB platform-control address".to_owned());
    }
    Ok(mmio_literals)
}

fn experiment_executable_end(sized_symbols: &str) -> Result<u32, String> {
    let mut executable_end = None::<u32>;
    for line in sized_symbols.lines() {
        let mut fields = line.split_whitespace();
        let Some(address) = fields
            .next()
            .and_then(|value| u32::from_str_radix(value, 16).ok())
        else {
            continue;
        };
        let Some(size) = fields
            .next()
            .and_then(|value| u32::from_str_radix(value, 16).ok())
        else {
            continue;
        };
        let Some(kind) = fields.next() else {
            continue;
        };
        if !matches!(kind, "t" | "T") || address < EXPERIMENT_ADDRESS || size == 0 {
            continue;
        }
        let end = address
            .checked_add(size)
            .ok_or_else(|| format!("symbol address overflow: {line}"))?;
        executable_end = Some(executable_end.map_or(end, |current| current.max(end)));
    }
    executable_end.ok_or_else(|| "probe ELF has no sized experiment text symbols".to_owned())
}

fn audit_probe_stack_sizes(stack_sizes: &str) -> Result<usize, String> {
    let mut maximum = None::<usize>;
    let mut found_entry = false;
    for line in stack_sizes.lines() {
        let mut fields = line.split_whitespace();
        let Some(size) = fields.next().and_then(|value| value.parse::<usize>().ok()) else {
            continue;
        };
        let function = fields.collect::<Vec<_>>().join(" ");
        found_entry |= function == "rust_experiment";
        maximum = Some(maximum.map_or(size, |current| current.max(size)));
    }
    let maximum = maximum.ok_or_else(|| "probe ELF has no stack-size records".to_owned())?;
    if !found_entry {
        return Err("probe ELF has no rust_experiment stack-size record".to_owned());
    }
    if maximum > USB_PROBE_MAX_STACK_BYTES {
        return Err(format!(
            "probe stack requirement {maximum} exceeds {USB_PROBE_MAX_STACK_BYTES} bytes"
        ));
    }
    Ok(maximum)
}

fn format_sha256(digest: [u8; 32]) -> Result<String, String> {
    use core::fmt::Write as _;

    let mut text = String::with_capacity(64);
    for byte in digest {
        write!(text, "{byte:02x}")
            .map_err(|error| format!("could not format SHA-256 digest: {error}"))?;
    }
    Ok(text)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct PackedProbeReport {
    container_bytes: usize,
    container_sha256: [u8; 32],
    payload_sha256: [u8; 32],
    payload_crc: u32,
}

fn pack_usb_probe(code: &[u8], artifact_dir: &Path) -> Result<PackedProbeReport, String> {
    let container = slimblade_verify::recovery_stub::build(code)
        .map_err(|error| format!("could not pack USB probe: {error}"))?;
    if !USB_RECOVERY_PROBE_ARTIFACT.code_matches(code) {
        return Err("USB probe code differs from its reviewed identity".to_owned());
    }
    let embedded_code = container
        .get(slimblade_image::APPLICATION_CODE_OFFSET..)
        .and_then(|payload| payload.get(..code.len()))
        .ok_or_else(|| "packed USB probe does not contain its complete code".to_owned())?;
    if embedded_code != code {
        return Err("packed USB probe code differs from the audited binary".to_owned());
    }
    let payload = container
        .get(slimblade_image::APPLICATION_PREFIX_OFFSET..)
        .ok_or_else(|| "packed USB probe has no updater payload".to_owned())?;
    let report = PackedProbeReport {
        container_bytes: container.len(),
        container_sha256: sha256(&container),
        payload_sha256: sha256(payload),
        payload_crc: updater_crc32(payload),
    };
    USB_RECOVERY_PROBE.validate(&container).map_err(|error| {
        format!(
            "USB probe container identity failed: {error}; actual container SHA-256 {}, payload SHA-256 {}, payload CRC {:08x}",
            format_sha256(report.container_sha256).unwrap_or_else(|_| "unavailable".to_owned()),
            format_sha256(report.payload_sha256).unwrap_or_else(|_| "unavailable".to_owned()),
            report.payload_crc,
        )
    })?;
    let path = artifact_dir.join("DO_NOT_FLASH-usb-recovery-probe.container.bin");
    fs::write(&path, container)
        .map_err(|error| format!("could not write {}: {error}", path.display()))?;
    Ok(report)
}

fn compile_usb_probe(firmware: &Path) -> Result<(), String> {
    run(firmware, "cargo", &[FIRMWARE_TOOLCHAIN, "fmt", "--check"])?;
    run(
        firmware,
        "cargo",
        &[
            FIRMWARE_TOOLCHAIN,
            "clippy",
            "--bin",
            USB_PROBE_BINARY,
            "--",
            "-D",
            "warnings",
        ],
    )?;
    run(
        firmware,
        "cargo",
        &[
            FIRMWARE_TOOLCHAIN,
            "build",
            "--release",
            "--bin",
            USB_PROBE_BINARY,
        ],
    )
}

fn build_usb_probe(root: &Path) -> Result<(), String> {
    let firmware = root.join("firmware/bk3635-usb-probe");
    compile_usb_probe(&firmware)?;

    let elf = firmware
        .join("target/thumbv5te-none-eabi/release")
        .join(USB_PROBE_BINARY);
    let artifact_dir = firmware.join("target/probe");
    fs::create_dir_all(&artifact_dir)
        .map_err(|error| format!("could not create {}: {error}", artifact_dir.display()))?;
    let code_path = artifact_dir.join("DO_NOT_FLASH-usb-recovery-probe.code.bin");
    eprintln!(
        "+ llvm-objcopy -O binary {} {}",
        elf.display(),
        code_path.display()
    );
    let status = Command::new("llvm-objcopy")
        .args(["-O", "binary"])
        .arg(&elf)
        .arg(&code_path)
        .current_dir(root)
        .status()
        .map_err(|error| format!("could not run llvm-objcopy: {error}"))?;
    if !status.success() {
        return Err(format!("llvm-objcopy exited with {status}"));
    }

    let code = fs::read(&code_path)
        .map_err(|error| format!("could not read {}: {error}", code_path.display()))?;
    let guard_path =
        root.join("firmware/bk3635-rs/target/guard/DO_NOT_FLASH-rust-marker-first-guard.code.bin");
    let guard = fs::read(&guard_path)
        .map_err(|error| format!("could not read {}: {error}", guard_path.display()))?;
    let report = audit_code(&code, &guard)
        .map_err(|error| format!("USB probe binary audit failed: {error}"))?;

    let elf_text = elf.to_string_lossy().into_owned();
    let defined = llvm_nm(root, &elf_text, "--defined-only")?;
    let undefined = llvm_nm(root, &elf_text, "--undefined-only")?;
    let symbols = audit_nm_outputs(&defined, &undefined)
        .map_err(|error| format!("USB probe symbol audit failed: {error}"))?;
    let sized_symbols = command_output(
        root,
        "llvm-nm",
        &[
            "-S".to_owned(),
            "--defined-only".to_owned(),
            elf_text.clone(),
        ],
    )?;
    let executable_end = experiment_executable_end(&sized_symbols)?;

    let disassembly = command_output(
        root,
        "llvm-objdump",
        &[
            "-d".to_owned(),
            "--triple=thumbv5te-none-eabi".to_owned(),
            format!("--start-address={EXPERIMENT_ADDRESS:#x}"),
            format!("--stop-address={executable_end:#x}"),
            elf_text.clone(),
        ],
    )?;
    let mmio_literals = audit_probe_disassembly(&disassembly, &code, executable_end)?;

    let stack_sizes = command_output(
        root,
        "llvm-readelf",
        &["--stack-sizes".to_owned(), elf_text],
    )?;
    let maximum_stack = audit_probe_stack_sizes(&stack_sizes)?;
    let packed = pack_usb_probe(&code, &artifact_dir)?;
    eprintln!(
        "USB probe PASS: {} code bytes, {} experiment bytes, {} reviewed MMIO literals, {} defined symbols, max stack {} bytes, code SHA-256 {}",
        report.code_bytes,
        report.experiment_bytes,
        mmio_literals,
        symbols.defined_symbols,
        maximum_stack,
        format_sha256(sha256(&code))?
    );
    eprintln!(
        "USB probe container: {} bytes, SHA-256 {}, payload SHA-256 {}, payload CRC {:08x}",
        packed.container_bytes,
        format_sha256(packed.container_sha256)?,
        format_sha256(packed.payload_sha256)?,
        packed.payload_crc
    );
    Ok(())
}

fn parse_address(value: &str) -> Result<usize, String> {
    let digits = value
        .strip_prefix("0x")
        .or_else(|| value.strip_prefix("0X"));
    digits
        .map_or_else(|| value.parse(), |hex| usize::from_str_radix(hex, 16))
        .map_err(|error| format!("invalid address {value:?}: {error}"))
}

fn disassemble_stock(
    root: &Path,
    firmware: &str,
    start: &str,
    stop: &str,
    state: &str,
) -> Result<(), String> {
    let firmware = Path::new(firmware);
    let image = fs::read(firmware)
        .map_err(|error| format!("could not read {}: {error}", firmware.display()))?;
    OFFICIAL_V449
        .validate(&image)
        .map_err(|error| format!("refusing image other than exact official v4.49: {error}"))?;
    let start = parse_address(start)?;
    let stop = parse_address(stop)?;
    if start >= stop || stop > image.len() {
        return Err(format!(
            "invalid disassembly range {start:#x}..{stop:#x} for {} bytes",
            image.len()
        ));
    }
    let triple = match state {
        "arm" => "armv5te-none-eabi",
        "thumb" => "thumbv5te-none-eabi",
        _ => return Err("state must be arm or thumb".to_owned()),
    };
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("system clock precedes Unix epoch: {error}"))?
        .as_nanos();
    let elf = env::temp_dir().join(format!("slimblade-disasm-{}-{nonce}.elf", process::id()));
    let objcopy = Command::new("llvm-objcopy")
        .args(["-I", "binary", "-O", "elf32-littlearm", "-B", "arm"])
        .arg(firmware)
        .arg(&elf)
        .current_dir(root)
        .status()
        .map_err(|error| format!("could not run llvm-objcopy: {error}"))?;
    if !objcopy.success() {
        return Err(format!("llvm-objcopy exited with {objcopy}"));
    }
    let result = Command::new("llvm-objdump")
        .arg("-D")
        .arg(format!("--triple={triple}"))
        .arg(format!("--start-address={start:#x}"))
        .arg(format!("--stop-address={stop:#x}"))
        .arg(&elf)
        .current_dir(root)
        .status()
        .map_err(|error| format!("could not run llvm-objdump: {error}"));
    let cleanup = fs::remove_file(&elf)
        .map_err(|error| format!("could not remove {}: {error}", elf.display()));
    let status = result?;
    cleanup?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("llvm-objdump exited with {status}"))
    }
}

fn usage() {
    eprintln!(
        "usage:\n  cargo xtask <check|rust-guard|usb-probe|postlink|all>\n  cargo xtask disassemble-stock FIRMWARE START STOP <arm|thumb>"
    );
}

fn main() -> ExitCode {
    let arguments: Vec<String> = env::args().skip(1).collect();
    let root = repository_root();
    let result = match arguments.as_slice() {
        [command] if command == "check" || command == "all" => host_checks(&root),
        [command] if command == "rust-guard" => build_rust_guard(&root),
        [command] if command == "usb-probe" => {
            build_rust_guard(&root).and_then(|()| build_usb_probe(&root))
        },
        [command] if command == "postlink" => post_link_checks(&root),
        [command, firmware, start, stop, state] if command == "disassemble-stock" => {
            disassemble_stock(&root, firmware, start, stop, state)
        },
        _ => {
            usage();
            return ExitCode::from(2);
        },
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        },
    }
}

#[cfg(test)]
mod tests {
    use super::{audit_probe_disassembly, audit_probe_stack_sizes, experiment_executable_end};

    fn literal_code(second: u32) -> Vec<u8> {
        let mut code = vec![0; 16];
        code.extend_from_slice(&0x0080_0020_u32.to_le_bytes());
        code.extend_from_slice(&second.to_le_bytes());
        code.extend_from_slice(&0x0080_6520_u32.to_le_bytes());
        code
    }

    #[test]
    fn disassembly_audit_resolves_only_actual_pc_relative_literals() {
        let disassembly = "\
21c4: 4802 ldr r0, [pc, #0x8] @ 0x2030\n\
21c6: 4903 ldr r1, [pc, #0xc] @ 0x2034\n\
21c8: 4a04 ldr r2, [pc, #0x10] @ 0x2038\n\
21ca: 9005 str r0, [sp, #0x14]\n\
21cc: 0080 lsls r0, r0, #0x2\n";

        assert_eq!(
            audit_probe_disassembly(disassembly, &literal_code(0x0080_4000), 0x2200),
            Ok(3)
        );
    }

    #[test]
    fn disassembly_audit_rejects_unreviewed_mmio_and_computed_pc() {
        let loads = "\
21c4: 4802 ldr r0, [pc, #0x8] @ 0x2030\n\
21c6: 4903 ldr r1, [pc, #0xc] @ 0x2034\n\
21c8: 4a04 ldr r2, [pc, #0x10] @ 0x2038\n";
        assert!(audit_probe_disassembly(loads, &literal_code(0x0080_6000), 0x2200).is_err());
        assert!(audit_probe_disassembly("21c4: 4687 mov pc, r0\n", &[], 0x2200).is_err());
        assert!(audit_probe_disassembly("21c4: f000 f800 bl 0x2084\n", &[], 0x2200).is_err());
    }

    #[test]
    fn stack_audit_requires_entry_and_enforces_limit() {
        assert_eq!(
            audit_probe_stack_sizes("176 rust_experiment\n56 helper\n"),
            Ok(176)
        );
        assert!(audit_probe_stack_sizes("300 rust_experiment\n").is_err());
        assert!(audit_probe_stack_sizes("56 helper\n").is_err());
    }

    #[test]
    fn sized_text_symbols_bound_disassembly_before_rodata() {
        let symbols = "\
000021c4 00000844 T rust_experiment\n\
00002a08 000000f0 t apply_response\n\
00002bc4 0000009a t packet_for\n\
00002c5e 00000000 r descriptor_data\n";

        assert_eq!(experiment_executable_end(symbols), Ok(0x2c5e));
    }
}
