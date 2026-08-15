use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{self, Command, ExitCode};
use std::time::{SystemTime, UNIX_EPOCH};

use slimblade_image::{OFFICIAL_V449, RECOVERY_GUARD, RECOVERY_GUARD_ARTIFACT};
use slimblade_verify::post_link::audit_nm_outputs;

const FIRMWARE_TOOLCHAIN: &str = "+nightly-2026-08-14";
const POST_LINK_ELFS: &[&str] =
    &["firmware/bk3635-rs/target/thumbv5te-none-eabi/release/slimblade-guard"];

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
    post_link_checks(root)
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
        "usage:\n  cargo xtask <check|rust-guard|postlink|all>\n  cargo xtask disassemble-stock FIRMWARE START STOP <arm|thumb>"
    );
}

fn main() -> ExitCode {
    let arguments: Vec<String> = env::args().skip(1).collect();
    let root = repository_root();
    let result = match arguments.as_slice() {
        [command] if command == "check" || command == "all" => host_checks(&root),
        [command] if command == "rust-guard" => build_rust_guard(&root),
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
