# Post-initialization recovery marker

Last checked: 2026-08-15

## Verified offline

Stock Thumb entry `0x19878` completes persistent-state setup, then conditionally
calls wired USB initialization at `0x19be4`. Both paths merge at `0x19bee`, just
before the permanent mode loop at `0x19bf2`. The mode byte is `0x00400282`; the
stock loop has handlers only for values `0`, `1`, and `2`.

The build-only `0459` candidate proves a dormant hook before making the marker
automatic:

1. Command `0x0e` calls the live-tested marker writer and only then stores
   reserved mode `3`; its response signature is `a3`.
2. Mode `3` follows an audited branch chain to the 12-byte hook at `0x22c0`.
3. The hook stores wired mode `2` and jumps to the unmodified loop at `0x19bf2`.
4. Command `0x0f` returns the current mode, allowing `3 -> 2` to be observed.

Modes `0`--`2` never enter the hook. Two debug strings remain NUL-terminated
but lose their line-feed byte to hold the dormant branch chain. Startup, USB,
IRQ/FIQ wrappers, mode handlers, and the marker writer are not displaced.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `24be6b6c2ae93694216d61043f54e0b7840a70f332e450888cc28773a252f7b5` |
| Container, 128,112 bytes | `133f5241efecc23c7cc2fffcc0fdb34c37f5a3f840362938c27a2bc5353c1de1` |
| Payload | `612e188cf000d7ecdabd0dd5e030b0066c93f59a2abef21ac03e496c38559c20` |
| Payload CRC | `806529df` |

`cargo xtask post-init-hook-probe` rebuilds and audits these identities without
accessing hardware. The candidate has not been flashed.

## Inference and remaining gate

Mode `3` is treated as reserved because every observed stock dispatch accepts
only `0`--`2`. A hardware test must still confirm normal input before arming,
response `a3`, a subsequent `0x0f` value of `2`, normal input afterward, and
power-cycle recovery to `25a7:fabe`/`d2`.

After that result, the next guarded probe calls the marker writer from the hook
while command `0x0e` has already committed a fallback marker. Only after that
passes should the marker call become automatic at the `0x19bee` boundary.
