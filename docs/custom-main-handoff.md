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
marker literals and storage operations are locked.

## Required hardware gate

The first run intentionally removes stock mouse processing and the main-loop
USB recovery command. After flashing, a USB power cycle must return resident
loader `25a7:fabe` and query result `d2`. That result proves the automatic
post-init marker completed before custom code.

## Hardware result

The exact `0472` container was flashed on 2026-08-16 after its locked identity
was reproduced. Resident loader query returned `d2`, and all 3,748 blocks
echoed. The application enumerated at the same physical path as `047d:80d7`,
`bcdDevice 0472`, with its 170-byte report descriptor; stock runtime behavior
was intentionally absent.

After five seconds without USB power, the application disappeared and the
same physical path returned as resident loader `25a7:fabe`. Its non-writing
query returned `d2`. This proves the automatic marker completed after stock
initialization and before the non-returning custom-main stand-in.

## `0473` USB-recovery custom main

The first custom main contains no mouse or sensor work. After the proven
automatic marker, it repeatedly calls stock vendor dispatcher `0x18f4d`.
Endpoint-zero reception remains in the untouched stock FIQ path; the dispatcher
handles command `0x0d` and calls stock endpoint-2 transmitter `0x1b4d0`.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `af65cdb33e14e99b0a253874d65a06c86ebb0d43937df640c42c6c5657907f18` |
| Container, 128,112 bytes | `7c044eb8381b87ea3e383a114c066c569040b16c1becdfe079d4940a4392d7fa` |
| Payload | `10bd22194a19c0c27d5120b461a7ff7a2897871ad13a255225d6e9953fcb3b5d` |
| Payload CRC | `7b3ca402` |

`cargo xtask custom-main-usb-recovery-probe` audits the exact image. The live
gate is application enumeration as `0473`, followed by command `0x0d` returning
the same physical path to loader `25a7:fabe`/`d2`.

## `0473` hardware result

The exact locked container was flashed on 2026-08-16. All 3,748 blocks echoed,
and the application enumerated at the same physical path as `047d:80d7`,
`bcdDevice 0473`, with its 170-byte report descriptor. Command `0x0d` then
returned that path directly to resident loader `25a7:fabe`; its read-only query
returned `d2`. The identical `0473` image was reflashed and is the active
development baseline.

This proves the custom-main boundary retains fast USB recovery independently
of stock mouse processing. The earlier `0472` cold-boot result remains the
fallback if later experimental USB code fails.

## Next implementation

Add continuous versioned sensor reports on endpoint `0x82`, giving recovery
responses priority. Experimental code must not write marker storage,
application flash, or protected startup.
