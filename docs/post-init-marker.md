# Post-initialization recovery marker

Last checked: 2026-08-15

## Historical `0459` candidate

Stock Thumb entry `0x19878` completes persistent-state setup, then conditionally
calls wired USB initialization at `0x19be4`. Both paths merge at `0x19bee`, just
before the permanent mode loop at `0x19bf2`. The mode byte is `0x00400282`; the
stock loop has handlers only for values `0`, `1`, and `2`.

The `0459` candidate attempted to prove a dormant hook before making the marker
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
accessing hardware. The hardware preflight below disproved its loop assumption.

## `0459` hardware preflight

The exact container was flashed on 2026-08-15: all 3,748 blocks echoed and the
application returned as `047d:80d7`, `bcdDevice 0459`, with its 170-byte vendor
descriptor and Linux input devices present. Read-only command `0x0f` returned
state `0`, not `2`, so the host stopped before command `0x0e`; no marker or hook
arm was written.

This falsifies `0x00400282` as the active wired-loop mode byte. Static review of
the running loop at `0x19b4a` identifies `0x00400264` instead. Its ARM switch
helper accepts cases `0`--`4` and sends values `>=5` through one default table
entry. The corrected `0460` design reserves value `5`, restores `0` in the
hook, and leaves all five stock cases unchanged.

## Corrected `0460` hardware result

The corrected container was flashed on 2026-08-15 after `cargo xtask check`
passed. All 3,748 blocks echoed, and the application returned at the same USB
path as `047d:80d7`, `bcdDevice 0460`, with the stock 170-byte descriptor and
Linux input interfaces present.

Command `0x0f` returned the required initial state `0`. Command `0x0e` then
committed the proven persistent marker, returned status `01` with signature
`a5`, and stored state `5`. Eight subsequent `0x0f` reads all returned `5`:
the dormant hook was not dispatched. No further experimental writes were sent.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `5a99f4d7ab6972f05724980a9d960f5b4d279212af3866ff8cb3c8a8b3b5dac0` |
| Container, 128,112 bytes | `61cf9ebc9b7739fbc586a6949a1dbca2f754f07b6e3e7ea16a4319c6d365bd87` |
| Payload | `3336ed10de4883b22e79f77e0f937245e289615237016d15c1987aaf3189dfbd` |
| Payload CRC | `d31dc8f2` |

## Inference and remaining gate

The state byte and USB command path are live, but the switch-helper table is not
re-read on each active-loop iteration as assumed. The exact dispatch path from
the state write to the next stock handler remains open.

Cold-power recovery passed on 2026-08-15. With the battery disconnected, a
five-second USB removal returned the same physical path as resident loader
`25a7:fabe`; its non-writing query returned device type `d2`. This proves the
marker was committed before the failed dormant route.

The loader then accepted all 3,748 blocks of the exact audited `0453` startup
trampoline (128,112 bytes, SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`).
The application returned at the same path as `047d:80d7`, `bcdDevice 0453`,
with its 170-byte report descriptor and Linux input interfaces present.

After recovery, restore the audited working image and trace the actual state
dispatch before another hook candidate. Only a live-proven hook should call the
marker writer, and only after that should marker placement become automatic.

## `0461` active-loop candidate

Static tracing explains the `0460` result. State `0` dispatches once from
`0x19b4a` into wired handler `0x1cf20`. That handler initializes its state and
then remains in an internal loop beginning at `0x1cfcc`; normal vendor commands
run without returning to the top-level switch.

The build-only `0461` candidate replaces the two Thumb instructions at
`0x1cfcc` with one `BL` to `0x22c0`. The shim branches to `0x22a0`, exactly
replays the displaced `ldr r7, =0x004002b8; ldr r0, [r7]`, and otherwise returns
without changing stock state. Only armed state `5` is consumed and restored to
`0`. Command `0x0e` still commits the proven marker before writing state `5`;
its distinct response signature is `a6`.

All code before the internal loop, the complete top-level switch, instructions
after `0x1cfcc`, the USB dispatcher, and IRQ/FIQ wrappers remain unchanged.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `aca3fcb6c3182a695667d96e2068e6e762698ae9f4f021cd3725d1ee6e308044` |
| Container, 128,112 bytes | `bf7aab32e3c32b4bf3853a7c79de21e5818961fbeb70239c95b40db7d898d077` |
| Payload | `dc240287646193279e2b46d582c635551ca64d020b81b5e68824e426c52ec40b` |
| Payload CRC | `df503f76` |

`cargo xtask active-loop-hook-probe` rebuilds and audits the exact candidate.

The exact container was flashed on 2026-08-15 after a clean rebuild reproduced
all pinned identities. Resident loader `25a7:fabe` answered `d2`, all 3,748
blocks echoed, and the application returned at the same physical USB path as
`047d:80d7`, `bcdDevice 0461`. Its stock 170-byte descriptor, stable vendor
symlink, and Linux input interfaces were present. Command `0x0e` has not yet
been sent, so the persistent marker and active-loop hook remain unarmed.

The user then confirmed normal ball movement, scrolling, and button operation
with the dormant `0461` hook installed. The remaining live gate is the explicit
marker-first arm: response signature `a6`, state transition `5 -> 0`, continued
normal input, and cold-power recovery to resident loader.

The marker-first arm was run on 2026-08-15. Preflight returned state `0`, and
command `0x0e` committed the marker and returned the exact `a6` signature.
Eight subsequent state queries all returned `5`; the hook at `0x1cfcc` did not
execute after the USB command. No further writes were sent.

This disproves `0x1cfcc` as a repeatedly visited live-loop boundary. It is an
initialization or outer-loop entry, while the running wired path remains in a
deeper control-flow cycle. Cold-power recovery and restoration of audited
`0453` are required before tracing that inner cycle.

Cold-power recovery passed: after five seconds without USB power, the same path
returned as resident loader `25a7:fabe` and answered `d2`. The loader accepted
all 3,748 blocks of the exact audited `0453` container (SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`).
The application returned as `047d:80d7`, `bcdDevice 0453`, with its 170-byte
descriptor and Linux input interfaces present.

## Next inner-loop target

Static tracing after the `0461` result identifies a deeper steady-state cycle:
`0x1d3c2` services a stock call at `0x15d34`, later branches through
`0x1d400–0x1d418`, and returns to `0x1d3c2`. The failed `0x1cfcc` boundary is
re-entered only under other state conditions.

A separately hashed `0462` candidate replaces only the four-byte `BL` at
`0x1d3c2` with a call to a wrapper. The wrapper calls the original stock target
through its odd Thumb address `0x15d35`, then consumes armed state `5`, and
returns to stock at `0x1d3c6`. The build audit caught and rejected an initial
relative-branch encoding before any identity was retained; the final wrapper
uses an explicit literal and `BLX`.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `df9df61f1b22393b242a24e9943795ea80bacb84cc3042ccae9a9e202bd8fc41` |
| Container, 128,112 bytes | `3defe9f5fda2ebaefb923fbe1c62fdd877345ccb75f6b1eec2604e731688d310` |
| Payload | `49bb7e6406fa78aebb7df9df10b79fbd7785091dfea5da4a83b0a259f476ec37` |
| Payload CRC | `8a544004` |

`cargo xtask steady-loop-hook-probe` rebuilds and audits the exact candidate.

The exact container was flashed on 2026-08-15 after a clean rebuild reproduced
all pinned identities. Resident loader `25a7:fabe` answered `d2`, all 3,748
blocks echoed, and the application returned at the same physical USB path as
`047d:80d7`, `bcdDevice 0462`. Its stock 170-byte descriptor, stable
`/dev/slimblade-vendor` symlink, and expected Linux input interfaces are
present. Command `0x0e` has not been sent, so the marker-first arm and wrapper
state path remain untested and no persistent recovery marker was written by
this probe run.

The user then confirmed normal ball movement, scrolling, and button operation
with the dormant `0462` wrapper installed. The next live gate is the explicit
marker-first `0x0e` arm: it must return signature `a7`, consume state `5` back
to `0`, and preserve normal input.

The marker-first arm was run on 2026-08-15. Preflight accepted the live device
and command `0x0e` wrote the recovery marker and armed state `5`, but eight
subsequent queries all found the state still armed. Therefore the wrapper at
`0x1d3c2` is not reached through the assumed live path after the command. This
candidate failed its control-flow gate; cold-power loader recovery and restore
of the audited `0453` image are required before further tracing.

Cold-power recovery then passed. With the battery disconnected, a five-second
USB removal returned the same physical path as loader `25a7:fabe`, whose
read-only query returned `d2`. The audited `0453` container was hash-checked as
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`;
all 3,748 restore blocks echoed. The application returned as `047d:80d7`,
`bcdDevice 0453`, with its 170-byte descriptor and expected Linux input
interfaces present.

The user confirmed normal ball movement, scrolling, and button operation after
the restore. This closes the `0462` experiment without loss of device function.

## Synchronous dispatcher-return candidate

The failed loop probes are unnecessary for the next gate. The proven live
vendor dispatcher at `0x18f4c` is called synchronously from `0x1c55a`:
command `0x0e` enters the injected handler through the existing call at
`0x18fba`, returns through the stock response path, and then returns to the
caller at `0x1c55e`.

The `0463` candidate replaces only the caller's four-byte `BL` with a call to
`0x22c0`. Its 28-byte wrapper calls the exact odd Thumb address `0x18f4d`,
preserves `r0`, checks state `5` only after the stock dispatcher returns,
restores state `0`, and returns to `0x1c55e`. This path is causally downstream
of the live command instead of depending on a loop being revisited. Command
`0x0e` retains marker-first ordering and uses signature `a8`.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `76e71f9937c503d709370bec7b889a2d974f655e571978de6f069332e22bdbbe` |
| Container, 128,112 bytes | `e79d8a05f0ed65ae6f3059885e02899c1adbb10be3d320f30829d1e8623b2656` |
| Payload | `257588ae7bcbfb1192221a0a2604ae10e776aab0c4526dc38ffcdf6992780191` |
| Payload CRC | `860c2809` |

`cargo xtask dispatcher-return-hook-probe` rebuilds and audits the exact
candidate. The full repository gate passes, including corruption tests for the
stock-call literal and patched call site. It has not been flashed. The safe
live sequence must enter loader through the proven marker-writing path, flash
the exact hash, confirm normal unarmed operation, and only then issue the
explicit marker-first arm.

The exact `0463` container was flashed on 2026-08-15 after read-only preflight
confirmed audited `0453` and a clean rebuild reproduced every pinned identity.
The proven stock command entered the same physical path as loader `25a7:fabe`,
whose non-writing query returned `d2`. All 3,748 blocks echoed, and the
application returned as `047d:80d7`, `bcdDevice 0463`, with its stock 170-byte
descriptor, stable vendor symlink, and expected Linux input interfaces.
Command `0x0e` has not been sent, so the explicit hook remains unarmed.

The user then confirmed normal ball movement, scrolling, and button operation.
This proves the dispatcher wrapper can run repeatedly in its unarmed state
without disrupting stock USB or input. The remaining live gate is the explicit
marker-first arm: response signature `a8`, state transition `5 -> 0`, and
continued normal input.

The explicit marker-first arm then passed on 2026-08-15. Preflight returned
state `00`; command `0x0e` committed the marker and returned exact signature
`a8`; the first subsequent query returned state `00`. This proves the
synchronous dispatcher-return wrapper consumed `5 -> 0` on the live command
path. The device remained `047d:80d7`, `bcdDevice 0463`, with its 170-byte
descriptor and expected Linux input interfaces present. Physical input and
cold-power recovery remain to be confirmed.

The user then confirmed normal ball movement, scrolling, and button operation
after the live `5 -> 0` transition. The only remaining `0463` safety gate is
cold-power recovery through the marker committed before the hook arm.

Cold-power recovery passed. With the battery disconnected, a five-second USB
removal returned the same physical path as resident loader `25a7:fabe`, whose
non-writing query returned `d2`. The audited `0453` container was verified as
SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`;
all 3,748 restore blocks echoed. The application returned as `047d:80d7`,
`bcdDevice 0453`, with its 170-byte descriptor and expected input interfaces.
This completes the `0463` functional and recovery gates.

The user confirmed normal ball movement, scrolling, and button operation after
the final restore. No device function was lost during the complete test.

## `0464` experiment dispatcher

The build-only `0464` candidate turns the proven `0463` boundary into a reusable
one-shot Rust entry. Command `0x0e` first commits the persistent recovery marker,
then writes state `5` and returns signature `a9`. The wrapper calls the exact
stock vendor dispatcher at odd Thumb address `0x18f4d`; after it returns, the
wrapper clears state `5` to `0` before calling Rust `experiment_entry` at
`0x22c0`. The initial Rust entry is a no-op that returns.

The wrapper saves `{r4, lr}`, preserving the 8-byte AAPCS stack alignment at
both nested call boundaries. Its stock-dispatch call, clear-before-Rust order,
Rust call target, return path, ELF geometry, symbols, headers, and exact image
are mechanically audited. Corruption tests cover the dispatcher literal, Rust
entry, and patched stock call site.

| Artifact | Identity |
| --- | --- |
| Injection, 340 bytes | `218eca02efff1692aa2c47603e11369c848f94f235f31c6cb50432efa0fdd8fb` |
| Container, 128,112 bytes | `dd720ba30fc05b9c401eb1f182f62bb217a57a03a3788ccc421806e06f30ac48` |
| Payload | `91069f91ac42e4621022514e04af0571ad5c9f52bbebcf192a8bdd9466a26e22` |
| Payload CRC | `70574845` |

`cargo xtask experiment-dispatch-guard` reproduces and audits the candidate.
The exact container was flashed on 2026-08-15 through resident loader
`25a7:fabe`; all 3,748 blocks echoed. It returned at the same physical USB path
as `047d:80d7`, `bcdDevice 0464`, with the stock 170-byte vendor descriptor.
Command `0x0e` has not been sent, so the marker and Rust experiment remain
unarmed. The remaining staged gates are normal unarmed input, explicit `a9`
arm with observed `5 -> 0`, normal input, then cold-power recovery and
restoration of audited `0453`.

The user confirmed normal ball movement, scrolling, and button operation with
the unarmed `0464` dispatcher installed. This passes the dormant-wrapper gate.

The explicit marker-first experiment passed on 2026-08-15. Preflight returned
state `00`; command `0x0e` committed the marker and returned exact signature
`a9`; the first subsequent query returned state `00`. The Rust no-op therefore
ran once and returned after the wrapper cleared its arm. The application
remained `047d:80d7`, `bcdDevice 0464`, with its 170-byte descriptor at the same
USB path. Physical input and cold-power recovery remain to be confirmed.

On 2026-08-16 the user confirmed normal ball movement, scrolling, and button
operation after the armed Rust entry. The host then rebooted; afterward the
device still identified as `047d:80d7`, `bcdDevice 0464`, with its 170-byte
descriptor, and no resident loader was present. This verifies survival of the
host reboot but not cold-power recovery because the USB port remained powered.

Cold-power recovery then passed. After five seconds without USB power, the same
physical path returned as resident loader `25a7:fabe`; its non-writing query
returned `d2`. This completes the `0464` unarmed, armed-return, normal-input,
host-reboot, and independent cold-power recovery gates. No restore image had
been written at the time of this observation.

The exact `0464` container was then reflashed as the development baseline. All
3,748 blocks echoed, and the application returned at the same USB path as
`047d:80d7`, `bcdDevice 0464`, with its 170-byte descriptor. The clean image
replaced the test marker, so the Rust experiment is unarmed again.
