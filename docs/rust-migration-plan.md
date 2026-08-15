# Rust migration plan

Last updated: 2026-08-15

## Progress

Completed 2026-08-15. All 88 former test cases have named Rust equivalents;
the Rust workspace currently runs 115 unit tests plus one compile-fail test.
Typed crates now own packet/CRC handling, image packing, artifact identities,
ELF and ARM/Thumb verification, Linux hidraw/sysfs access, exact-hash command
gates, loader discovery, and the complete 3,748-block transfer.

Cargo produces the live-proven 422-byte marker-first guard and 128,112-byte
container exactly. The Rust hardware cutoff flashed that guard, observed USB
silence, recovered `25a7:fabe` with `B2/d2` after a USB power cycle, restored
the exact v4.53 image, and confirmed `047d:80d7`, `bcdDevice 0453`, and the
170-byte descriptor. The user confirmed normal movement, scrolling, and
buttons. Superseded Python implementations and Makefile orchestration were
then removed; retained C/assembly and the BK3633 SDK are research references.

## Goal

Replace active Python host tooling and C firmware logic with readable, typed,
well-tested Rust without changing any established protocol decision, safety
boundary, or reference artifact. Rust becomes the only active high-level
implementation language. Linker scripts and the minimum audited ARM/Thumb
assembly remain where exact processor behaviour matters. The vendored BK3633
SDK remains an unbuilt reference.

Migration is incremental. A legacy component is removed only after its Rust
replacement passes differential tests and the applicable artifact or hardware
gate.

## Non-negotiable gates

1. Existing generated artifacts remain byte-for-byte identical until a later
   experiment intentionally changes the post-marker payload.
2. Every current test case gains an equivalent Rust test with the same inputs,
   expected outputs, corruption cases, and failure boundary.
3. Flashing retains exact-hash confirmation, identity checks, `B2/d2` proof,
   same-port re-enumeration checks, and the rule that nothing retries after
   `B0` may have erased flash.
4. The live-proven marker-writing prefix remains byte-identical and executes
   before all experimental code.
5. Experimental firmware never links persistent-storage drivers and fails
   preflight on forbidden MMIO literals, unsafe calls, unexpected symbols, or
   writes below application offset `0x2000`.
6. Kensington firmware and updater binaries remain external inputs and are
   never committed.
7. Hardware writes remain separate from ordinary tests and require an explicit
   user request.

## Reference artifacts

Rust parity must reproduce these current SHA-256 values from the same inputs:

| Artifact | Code SHA-256 | Container SHA-256 |
| --- | --- | --- |
| Stock startup reference | `60d7616f48e2e457787e28748aec0b8afd404af35094cc8ef6b74c660c9248d8` | n/a |
| Stock IRQ/FIQ wrappers | `02e811fe3f434dd0fc697621bfbdc9cd74eee2d1e5d16df93f94f15fe7e5df9d` | n/a |
| Recovery carrier | `6dfab1b623c6fbd8daa6be71bdb3bfad1e90808da90956dc671c0165544dbd2e` | `e555d5e17edc84cb8799d035d6193f6f664c1df9116bcba3c49faef1609221e8` |
| Reset trampoline | `eb26dace22b23177e84b62225949e573cd2b2764add0a722411733f3cb2a57f2` | `bad4a3a7bdf3610e8b6cf0d9b1bb27f4d147ffa0efb242f24c0257bb454c6905` |
| Startup trampoline v4.53 | `0e24e9ffbf218afabde39043b177f19e29761b3175b772351fb6f7a839a800f7` | `dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b` |
| Standalone recovery stub | `d88b2cd9211d9c46914062770e024f409dcee75ec826e70e80f6ff9a9e353bfe` | `34daf13778a79034cc3a35917fbe6cfacc0b2f93db650e50f1f4df98ecf7e618` |
| Marker-first hang guard | `93eef0420d1a54e4ca7efbfa1ca6a30e79044ff91b4294584ab062b7c6e061c0` | `7bb3055bc1575bcb9ca4eab9ba2a83a3dbaba131e92cca78fffb18397cc2d19a` |

The Rust verifier must also preserve every recorded payload hash, CRC, changed
offset, call target, ELF constraint, and USB packet vector in the current test
suite. Official v4.49 and descriptor-probe validation remain covered even
though those external images are absent.

## Target layout

```text
Cargo.toml                         stable host workspace
rust-toolchain.toml               pinned stable host toolchain
crates/
  slimblade-protocol/             no_std packets and checksums
  slimblade-image/                containers, CRCs, manifests
  slimblade-verify/               ELF, instruction and safety checks
  slimblade-linux/                hidraw, ioctl, poll and sysfs
  slimblade-cli/                  read-only and guarded write commands
xtask/                            build, parity and preflight orchestration
firmware/bk3635-rs/
  Cargo.toml                      separate no_std firmware workspace
  rust-toolchain.toml             pinned nightly with rust-src
  .cargo/config.toml              thumbv5te target and linker flags
  src/                            guard, HAL and experimental application
  link/                           reviewed linker scripts
tests/fixtures/                   synthetic packets, ELF files and transcripts
research/probes/                  retained milestone sources and notes
vendor/bk3633_sdk/                immutable reference; never linked
```

`slimblade-protocol` avoids allocation and is shared by the host and firmware.
Linux-specific and flashing code cannot enter the firmware dependency graph.
The firmware workspace uses `thumbv5te-none-eabi`, `#![no_std]`, panic abort,
and nightly `build-std = ["core"]`; all application source stays within stable
Rust language features.

## Migration stages

### 0. Freeze the baseline

- Record host Clang/LLVM, Python and Rust versions plus all reference hashes.
- Add a machine-readable parity manifest mapping every legacy artifact,
  command and Python test to its Rust replacement.
- Capture synthetic USB transcripts for identity, `B2`, `B0`, every `B1`
  variant, erase statuses, disconnects and re-enumeration. Do not capture or
  commit proprietary firmware bytes.
- Make one command run all 88 legacy tests and all build preflights.

Exit gate: a clean checkout with the external v4.49 input reproduces the table
above twice, and the current suite passes unchanged.

### 1. Establish the Rust workspaces

- Pin stable host and dated nightly firmware toolchains; commit both lockfiles.
- Add formatting, Clippy and test commands through `cargo xtask`.
- Deny warnings, undocumented unsafe blocks, unsafe operations in unsafe
  functions, panicking convenience APIs, floating arithmetic and integer
  division in firmware.
- Document every dependency and keep the host dependency set small. Prefer
  direct hidraw access over libusb or a second device-discovery stack.

Exit gate: empty host and firmware programs build reproducibly from a clean
target directory, and CI-equivalent checks run through one documented command.

### 2. Port pure protocol and image logic

- Introduce fixed-size report types for 17-byte application and 49-byte loader
  reports; invalid lengths and report IDs must be unrepresentable after parse.
- Port updater checksum, CRC, header parsing, padding and application packing.
- Port ARM/Thumb branch encoders and decoders with checked alignment and range
  types.
- Port artifact identities into typed manifests rather than repeated constants.
- Add table tests for every current packet hex value and property tests for
  parse/serialize round trips, truncation, overflow and one-byte corruption.
- Differentially compare every Rust output with Python before accepting it.

Exit gate: all pure Python tests have mapped Rust tests; packed containers and
all packet bytes are identical.

### 3. Port verifiers and builders

- Parse ELF32 sections, symbols, relocations, entry points and ARM attributes
  in Rust using checked bounds and explicit little-endian types.
- Port each carrier, trampoline, startup, stub and guard verifier independently.
- Preserve exact JSON report fields during overlap so reports can be compared
  structurally.
- Port stock-derived image patching to Rust. Firmware instructions must come
  from compiler/assembler output, not byte strings in host code.
- Add negative tests for each existing rejected mutation and fuzz the container
  and ELF parsers for panics and out-of-bounds access.
- Build each artifact twice from clean directories and compare every byte.

Exit gate: the complete reference table and verifier reports match; every
legacy verifier test has an equivalent Rust test.

### 4. Port read-only Linux access

- Implement a small `Hidraw` wrapper with owned file descriptors and isolate
  all ioctl unsafety in one reviewed module.
- Port identity, name and report-descriptor queries, nonblocking reads, polling,
  sysfs parent discovery and stable-path resolution.
- Put filesystem and transport operations behind traits. Test with temporary
  sysfs trees, pipes and scripted transports rather than real hardware.
- Reproduce `identify`, descriptor and report-capture output before changing
  the CLI presentation.

Exit gate: offline tests pass and live read-only results match Python for the
170-byte descriptor and `047d:80d7` identity.

### 5. Port the loader state machine

- Model discovery, queried loader, erase, download, completion and expected
  re-enumeration as explicit states.
- Require `B2/d2` before exposing the erase transition.
- Preserve all 3,748 block echoes, timeout rules, progress accounting, final
  CRC behaviour, same-port checks and expected-silence handling.
- Inject failure at every state and representative block boundaries. Prove no
  write occurs when discovery fails and no automatic retry occurs after `B0`.
- Keep exact SHA confirmation in the Rust command type, not as an unstructured
  string checked deep inside the transfer routine.

Exit gate: scripted transcripts produce the same writes, decisions and exit
codes as Python for success and every currently tested failure.

### 6. Validate the Rust host on hardware

Status: complete on 2026-08-15.

- Run identity and descriptor commands first.
- Enter the resident loader through the proven application command and issue
  only the non-writing `B2/d2` query.
- With a separate explicit request, restore the exact v4.53 image using Rust.
- Confirm all 3,748 echoes, `bcdDevice=0453`, the descriptor and physical ball,
  scroll and button behaviour.
- Retain the Python flasher unchanged until this complete restore passes.

Exit gate: Rust completes one live known-image restore with results equal to
the proven Python process.

### 7. Rebuild the proven firmware boundary in Rust

Status: complete on 2026-08-15, including the explicit hardware flash.

- Keep the live-proven reset/vector, marker and ARM/Thumb sequences as reviewed
  assembly included by the Rust firmware crate. Do not ask LLVM to rediscover
  byte-critical recovery instructions.
- Replace C glue with `extern "C"` Rust entry points and a minimal panic loop.
- Link the two-byte hang as the first Rust experimental payload.
- Require the raw 422-byte guard and full container to match their recorded
  hashes exactly, including all seven differences from the standalone stub.
- Verify symbols, sections, calls, MMIO literals, persistent-storage isolation,
  first-8-KiB exclusion and absence of unwanted compiler helpers.

Exit gate: the Rust-built hang guard is byte-identical and passes the complete
existing guard preflight. A hardware flash still requires a separate explicit
request.

### Post-parity crate review

After the Rust recovery guard and trampoline chain reaches complete feature and
byte parity, research maintained crates that could replace custom ELF parsing,
binary image headers, checked ARM/Thumb addresses and branches, or peripheral
register access. Evaluate malformed-input behaviour, dependency size,
maintenance, licenses, `no_std` and ARMv5 support, and generated bytes. Replace
custom code only when its tests and exact artifact gates remain equally strict.

### First post-parity development milestone

After the Rust guard matches the proven 422-byte guard exactly, add a guarded
USB command that requests the resident loader without disconnecting USB power.
It must preserve the marker-first invariant, use the proven reset path, verify
same-port loader re-enumeration, and retain physical power cycling as the
independent recovery fallback. This is intended to shorten the firmware test
cycle; it must not weaken recovery or be combined with the parity flash.

### 8. Introduce safe Rust experimental firmware

- Create one audited volatile-MMIO module; safe code receives typed peripheral
  handles and cannot construct storage or flash controllers.
- Add functionality in recoverable increments: RAM-only logic, observable
  GPIO, USB control/report path, buttons, individual sensors, then combined raw
  sensor reports.
- Keep the marker set for the entire experiment. Power cycling must always
  enter the resident loader.
- Host-test packet processing and sensor mathematics; hardware-test only the
  peripheral boundary.
- Treat each intentional payload change as a new artifact with its own manifest,
  preflight report and exact confirmation hash.

Exit gate: each increment passes host tests, ELF safety checks and the
marker-first recovery procedure before the next peripheral is introduced.

### 9. Retire legacy implementations and tidy the repository

Status: complete on 2026-08-15. Milestone C/assembly remains in its original
documented locations as unbuilt reference source.

- Remove a Python or C implementation only when its parity-manifest row is
  complete and its Rust replacement has passed the corresponding exit gate.
- Replace repeated Makefile orchestration with `cargo xtask`; retain linker
  scripts and readable architecture assembly.
- Retain historical carrier and trampoline sources in their documented
  directories as unbuilt research references.
- Remove Python caches and generated products from the tree; keep all build
  output ignored under `target/` or explicit build directories.
- Consolidate active documentation into architecture, recovery, development
  and hardware references while preserving dated research evidence.
- Delete the parity harness and Python runtime dependency only after the Rust
  host restore and Rust guard gates both pass.

Exit gate: a clean checkout needs Rust, LLVM binutils and the external stock
image only; one command formats, lints, tests, builds, verifies and reports all
artifacts. `rg` finds no active Python or C implementation, and the full safety
and test matrices remain covered.

## Definition of done

- Rust is the only active high-level implementation language.
- Host tooling builds on pinned stable Rust; firmware builds on pinned nightly.
- Existing reference artifacts are byte-identical and future artifacts preserve
  the exact recovery prefix.
- Every legacy test has a named Rust equivalent and no safety assertion was
  weakened during migration.
- Host logic is fully testable without hardware through typed fake transports.
- Unsafe Rust is small, documented and confined to hidraw ioctl, MMIO and
  architecture entry boundaries.
- The resident-loader cold-boot recovery and known-image restore have both been
  demonstrated using the Rust toolchain before legacy flashing code is removed.
