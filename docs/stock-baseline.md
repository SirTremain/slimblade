# Stock baseline

Initially recorded 2026-10-16 from the [pre-reset repository](legacy.md), whose
firmware inspection date was 2026-08-14. The later same-day
[bootstrap session](bootstrap.md) freshly downloaded the official package,
verified every artifact below, and checked startup anchors with Ghidra and
LLVM. No device inspection was performed.

## Recorded observations

The official v4.49 updater package is a useful initial analysis baseline.
Its embedded resource is
`USBUpdateTool.MakeUpgradeTool.Files.CompxUpgradeBinFile.bin`.
The [machine-readable baseline](../decomp/baseline.json) preserves its identity.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Official v4.49 ZIP | 1,037,410 | `dffe13ab063cb9614669914295b273bda0e5906bc5af75b3f73cd2da5f0f41ac` |
| Updater EXE | 3,008,000 | `38fc1b333d316039e4eb732c70183b8c6c4cc831c90246425917e9dce64f7688` |
| Firmware resource/container | 128,112 | `e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7` |
| Payload at container offset `0x2000` | 119,920 | `3b7849cafa2a8d4a0c2694c9771d70563563dc1c6cdbf84ede9b8648071604bf` |

Source: [ACCO Brands Japan v4.49 package](https://accobrands.co.jp/wp/wp-content/uploads/Kensington-Slimblade-Pro-V4.49.zip),
historically retrieved 2026-08-14 and revalidated 2026-10-16. All four hashes
matched. A different hash must become a separate baseline.

The old updater analysis records payload transfer to address `0x2000`.
Application metadata precedes ARM vectors at `0x2020`; the reset target is
`0x2064`, with a later Thumb entry at `0x19878` (pointer `0x19879`). The old
startup analysis records `.data` copied from `0x1ed60` to `0x400020` for `0x6f4`
bytes and `.bss` cleared at `0x400714` for `0x3940` bytes. These are anchors to
check, not an exhaustive memory map or approved function boundaries.

The previous board was marked `BK3635UQN56A`. Existing analysis uses a
little-endian ARMv5TE/ARM968E-S model with ARM/Thumb interworking. Related
BK3633 source is helpful for hypotheses, but its RAM limits, watchdog driver
and some peripheral names disagree with the observed BK3635 firmware.

## Inferences and unresolved questions

- Use the full resource mapped at address zero as an initial *analysis model*;
  verify headers and each region before treating offsets as runtime addresses.
  Do not assume the first `0x2000` bytes are a complete resident loader dump or
  that the updater resource contains all device storage.
- The original compiler, version, ABI, flags, linker script and libraries are
  unknown. Ghidra's compiler-spec selection does not identify that toolchain.
- Function boundaries, literal pools, indirect calls, tables, RAM aliases and
  unclassified bytes need continued review. Six [pilot](pilot.md) leaves have
  local boundary approval; the global inventory and total function count remain
  unknown. See the [dependency ledger](dependencies.md).
- The replacement device's revision and installed firmware remain unknown.
  Studying v4.49 does not require changing that device.
- Full stock reconstruction includes all wireless behavior. The later custom
  branch should retain it unless measured size limits require removal, as set
  out in the [project plan](project-plan.md). A byte-identical resource rebuild
  does not reconstruct EEPROM, factory calibration, external ROM or other
  storage absent from the resource.

The previous `0475` experiment made the recovery marker unreachable despite
retaining its writer. Keep the [reachability gate](marker-reachability-gate.md)
for modified firmware in the plan's separately requested hardware phase. Do not
add that custom marker to an exact-match stock artifact.
