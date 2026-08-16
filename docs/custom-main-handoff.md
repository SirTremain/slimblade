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

The build-only `0474` transport gate runs the stock wired/sensor initializer,
then falls into a 148-byte Rust runtime at reclaimed stock-loop range
`0x1c460..0x1c4f4`. It emits version-1 zero-motion reports on endpoint `0x82`.
The stock dispatcher runs first on every pass, and all six stock transmitter
readiness predicates must pass before a stream report is submitted.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `54b54999d5aab57900cb47f3521c92b1807dbdb2a988bf8afd805fd6f6d02124` |
| Rust runtime, 148 bytes | `9dba72994d1356fabe977f8c8d4a9af980302465839991322fade7e439e4b672` |
| Container, 128,112 bytes | `31c14d3a51a94ccc8f2d5337bae15b3755ee7665804d56416ac518d44decb489` |
| Payload | `964e7fa847e308fa51d173e1cac1ae3b97d61c73b9f82c03268341871768c362` |
| Payload CRC | `105bca99` |

The live gates are eight valid sequence-changing reports, followed by command
`0x0d` returning the same path to loader. After that, replace the zero fields
with accumulated sensor and button state. Experimental code must not write
marker storage, application flash, or protected startup.

## `0474` hardware result

The exact container was flashed on 2026-08-16. All 3,748 blocks echoed and the
application enumerated at the same physical path as `047d:80d7`,
`bcdDevice 0474`. Eight unsolicited checksum-valid reports arrived with
consecutive sequences `4977..4984`. Command `0x0d` then returned the same path
to resident loader `25a7:fabe`, whose query returned `d2`, while the stream was
active. The identical `0474` image was reflashed as the development baseline.

This proves the reclaimed runtime region, Rust report construction, stock
endpoint-2 transmitter, and fast recovery coexist without stock mouse-loop
execution.

## `0475` sensor-stream candidate

The next audited image retains the `0474` marker, handoff, wired initializer,
USB dispatcher, and transmitter. It adds one veneer for stock sensor service
`0x1a74c` and patches the live-proven pre-clear boundary at `0x1a798`. The hook
copies sensor A (`0x00400174/176`) and B (`0x004001da/1dc`) into the proven
inactive shadow at `0x00401360` and replays the displaced clear.

The Rust loop clears the shadow before each synchronous sensor call, saturates
four signed accumulators and the sample count, and clears them only after the
stock endpoint-2 transmitter accepts a report. Recovery dispatch remains the
first call in every loop. Buttons remain zero in this candidate.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `aa0991589fc2242a19fd824742b567344e33aa60270e4466ba65e01146980a79` |
| Rust runtime, 296 bytes | `febc0f904f4cf3bd98caa4900862fc5573a43204a32e2e0fed32542e9bebe293` |
| Sensor support, 108 bytes | `c85b576bebf9044dc38848eb9e9d0260544b8b3c3793720ae296f8263ce4213b` |
| Container, 128,112 bytes | `65c7dfd35d4f97751db74899c076c27741dd290d045fbd130aa854443b60edf8` |
| Payload | `b00d22b8ab6ae686cc6a3230324c971a57bf29a43e5236bd94ee8c69d05e4ae9` |
| Payload CRC | `c430b50f` |

The runtime ends at `0x1c588`, leaving the wired initializer's literal island
`0x1c58c..0x1c5bf` byte-identical. Sensor support at `0x1c5c0..0x1c62b`
replaces only wireless-mode code, which is outside the wired-only target.

## `0475` live failure

The exact locked image enumerated as `047d:80d7`, `bcdDevice 0475`, but did not
provide usable HID input. Repeated direct USB endpoint-zero transfers of the
exact command `0x0d` were accepted by Linux usbfs, including 963 transfers in
one 60-second run, without reaching the resident loader. A complete USB power
removal with the battery disconnected also returned to `0475`, not the loader.

This falsifies two safety assumptions: the code at `0x1c5c0..0x1c62b` was not
proved unreachable before the post-init marker handoff, and successful USB
control-transfer completion does not imply that the main-loop vendor dispatcher
ran. The image is retained for analysis but the CLI refuses to flash it again.
Recovery of the live board now requires a separately verified hardware path;
`RSTN`, `P04` through `P07`, `VCC`, and `GND` remain the likely factory SPI/JTAG
pad cluster, but their BK3635-specific programming contract is not yet proven.

Static reinspection identifies the direct failure path. Stock USB setup occurs
before the top-level mode loop, explaining why `0475` can enumerate. That loop
then calls stock handler `0x1c5c0`, which must write mode `0` before the later
`0x19c08 -> 0x22c0` marker handoff becomes reachable. `0475` replaced the
handler entry with a sensor hook that assumes an entirely different register
contract and does not perform the mode write. The device therefore remains in
the pre-handoff loop until its watchdog resets. The persistent `marker_set`
routine is never called; this explains why cold power repeatedly launches the
application instead of the resident loader.

A coordinated battery-disconnected power cycle was captured with the kernel
USB-event monitor on 2026-08-16. Every device-add event was
`PRODUCT=47d/80d7/475`; none used any known loader identity. The application
remained enumerated for roughly 1.3 seconds, disappeared for roughly 2.1
seconds, and repeated with a new USB device number. This is consistent with a
watchdog-reset loop and rules out an observable split-second loader interval.
