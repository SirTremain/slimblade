use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

const LEGACY_PREFLIGHTS: &[&str] = &[
    "vendor/bk3633_sdk/SDK/projects/slimblade_wired",
    "firmware/recovery_carrier",
    "firmware/reset_trampoline",
    "firmware/startup_trampoline",
    "firmware/recovery_stub",
    "firmware/recovery_guard",
];
const FIRMWARE_TOOLCHAIN: &str = "+nightly-2026-08-14";

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("xtask must remain directly below the repository root")
        .to_path_buf()
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
            "--",
            "-D",
            "warnings",
        ],
    )?;
    run(
        &firmware,
        "cargo",
        &[FIRMWARE_TOOLCHAIN, "build", "--release"],
    )
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
    Ok(())
}

fn usage() {
    eprintln!("usage: cargo xtask <check|legacy|all>");
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
        "legacy" => legacy_checks(&root),
        "all" => host_checks(&root).and_then(|()| legacy_checks(&root)),
        _ => {
            usage();
            return ExitCode::from(2);
        }
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
