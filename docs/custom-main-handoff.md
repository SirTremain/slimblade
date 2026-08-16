# Custom-main handoff

Last checked: 2026-08-16

## Verified

- Thumb entry `0x19878` performs global initialization and calls stock USB
  initialization at `0x19be4` on the wired path.
- The top-level mode loop begins at `0x19bee`. Its mode byte is
  `0x00400282`; mode `0` has exactly one call site, `0x19c08 -> 0x1c410`.
- Handler `0x1c5c0` writes mode `0` at `0x1c6d8` before returning. The next
  dispatch enters `0x1c410`, which contains the live-proven wired vendor
  dispatcher at `0x1c55a`.
- Complete stock startup invalidates an early reset-trampoline marker. The
  recovery marker must be written after this initialization.

## `0472` build-only gate

The candidate changes the call at `0x19c08` to `0x22c0`. The handoff preserves
8-byte stack alignment, calls the live-tested `marker_set` at `0x21d8`, and
then deliberately hangs. It cannot reach stock mouse processing or return from
custom code before the marker operation completes.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `a99871f28c1ee714959376bb008447f874e0bcdaaed3c21d09931df78d98739a` |
| Container, 128,112 bytes | `401ab888a8512fa6ff74058fc78d329a3e4a34064614542ea3716d06be8dbf97` |
| Payload | `3d5a0008095ca4ff3e486912842b619c8c9286b0e0702932345e644fb6ea0661` |
| Payload CRC | `73c3cfbe` |

`cargo xtask custom-main-handoff-probe` rebuilds and audits the exact image.
The stock reset-to-handoff path, wired transition handler, IRQ/FIQ wrappers,
marker literals and storage operations are locked. The image has not been
flashed.

## Required hardware gate

The first run intentionally removes stock mouse processing and the main-loop
USB recovery command. After flashing, a USB power cycle must return resident
loader `25a7:fabe` and query result `d2`. That result proves the automatic
post-init marker completed before custom code.

## Next implementation

Replace the deliberate hang with a Rust `custom_main()`. It may reuse stock
USB endpoint-2 submission and sensor initialization initially, but must not
write marker storage, application flash, or protected startup. Normal mouse
reports are not required; a host process may translate raw reports later.
