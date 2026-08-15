use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

use slimblade_image::{RECOVERY_GUARD, RECOVERY_GUARD_ARTIFACT};
use slimblade_verify::post_link::audit_nm_outputs;

const LEGACY_PREFLIGHTS: &[&str] = &[
    "vendor/bk3633_sdk/SDK/projects/slimblade_wired",
    "firmware/recovery_carrier",
    "firmware/reset_trampoline",
    "firmware/startup_trampoline",
    "firmware/recovery_stub",
    "firmware/recovery_guard",
];
const FIRMWARE_TOOLCHAIN: &str = "+nightly-2026-08-14";
const POST_LINK_ELFS: &[&str] = &[
    "vendor/bk3633_sdk/SDK/projects/slimblade_wired/build/stock-startup-reference.elf",
    "firmware/recovery_carrier/build/DO_NOT_FLASH-stock-recovery-carrier.elf",
    "firmware/reset_trampoline/build/DO_NOT_FLASH-stock-reset-trampoline.elf",
    "firmware/startup_trampoline/build/DO_NOT_FLASH-stock-startup-trampoline.elf",
    "firmware/recovery_stub/build/DO_NOT_FLASH-recovery-stub.elf",
    "firmware/bk3635-rs/target/thumbv5te-none-eabi/release/slimblade-guard",
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
    run(root, "cargo", &["test", "--workspace"])
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

fn legacy_checks(root: &Path) -> Result<(), String> {
    run(
        root,
        "python3",
        &[
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ],
    )?;
    for directory in LEGACY_PREFLIGHTS {
        run(root, "make", &["-C", directory, "preflight"])?;
    }
    run(root, "cargo", &["test", "--workspace"])?;
    post_link_checks(root)
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

fn usage() {
    eprintln!("usage: cargo xtask <check|rust-guard|legacy|postlink|all>");
}

fn main() -> ExitCode {
    let mut arguments = env::args().skip(1);
    let Some(command) = arguments.next() else {
        usage();
        return ExitCode::from(2);
    };
    if arguments.next().is_some() {
        usage();
        return ExitCode::from(2);
    }

    let root = repository_root();
    let result = match command.as_str() {
        "check" => host_checks(&root),
        "rust-guard" => build_rust_guard(&root),
        "legacy" => legacy_checks(&root),
        "postlink" => post_link_checks(&root),
        "all" => host_checks(&root).and_then(|()| legacy_checks(&root)),
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
