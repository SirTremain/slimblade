# Marker-first experiment-entry probe

Last checked: 2026-08-15

## Purpose

The `0457` probe retains the complete stock startup, USB stack, input handling,
interrupt wrappers, and recovery command `0x0d`. Explicit post-startup command
`0x0e` runs the live-tested persistent marker writer and then enters a deliberate
Thumb self-loop instead of returning to stock. This tests recovery from custom
code that has broken application USB.

The reset path does not touch persistent storage. No experimental code can run
before stock USB receives `0x0e`.

## Verified offline

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Linked injection | 340 | `f8f97b226a2d293560bb2103ee6d0c0cd9a026c3260798795946c2b3c05f6897` |
| Full container | 128,112 | `bc3275a95a0ebd4f3c12863ed2607d5f9ce026903ef19f145e177834f1a988b3` |
| Updater payload | 119,920 | `08a4201ef3d9656b720914ac86447fdae27463e0302f7edd6f4641186b3e8fa9` |

Payload CRC is `2381ed73`; USB `bcdDevice` is `0457`. The exact base remains
the audited v4.53 container SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`.

The injection differs from the live-tested `0456` injection at only offsets
`0x18–0x19`: marker-return instruction `10 bd` is replaced by self-loop
instruction `fe e7`. The preceding push and call to the marker routine, all
marker/storage instructions and literals, reset trampoline, stock continuation,
dispatcher, IRQ/FIQ bytes, and zero-filled gap are unchanged. The verifier
requires this exact two-byte delta and rejects a return after the marker.

`cargo xtask check` passes all workspace and firmware format, lint, test,
`no_std`, post-link, ELF, hash, header, branch, and negative-corruption gates.
No build or test command accesses hardware.

## Proposed live sequence

1. From resident loader `25a7:fabe`/`d2`, flash only the exact locked `0457`
   container and require application `047d:80d7`, `bcdDevice 0457`.
2. Confirm movement, scrolling, buttons, and normal stock USB before starting
   the experiment.
3. Send `start-experiment --confirm`. Require the `0x0e` report write to
   complete and require no vendor response, matching the deliberate hang.
4. Remove USB power with the battery disconnected, restore power, and require
   resident loader `25a7:fabe` with query response `d2`.

## Verified live

On 2026-08-15, the resident loader answered `d2` and accepted all 3,748 blocks
from the exact locked container. The application re-enumerated on the same USB
path as `047d:80d7`, `bcdDevice 0457`, with the unchanged 170-byte report
descriptor. The marker was not set and the experiment was not entered during
this stage. The user confirmed ball movement, scrolling, and buttons still
worked normally. Marker-then-hang recovery remains open.

Command `start-experiment` then wrote the `0x0e` report successfully and no
vendor response arrived during the three-second observation window, matching
the deliberate non-returning path. This alone does not prove the persistent
marker; the cold-boot loader result remains the decisive check.

The user confirmed ball movement, scrolling, and buttons stopped after the
command, consistent with execution remaining in the intended self-loop.

With the battery disconnected, USB power was then removed for at least five
seconds and restored. Without any application-side USB command, the device
enumerated directly as resident loader `25a7:fabe` and returned query response
`d2`. This completes the live gate: the late marker committed before the
deliberately hanging experimental entry.

## Result if the live gate passes

Each later experiment can replace only the final self-loop. Entry remains an
explicit stock-USB command after initialization; the guard writes and commits
the recovery marker first. Code that returns control to the stock dispatcher
retains command `0x0d` as the fast loader path; code that takes over USB must
provide an equivalent trigger. If either path hangs, removing USB power is the
independent loader fallback.
