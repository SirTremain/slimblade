# Late-marker compatibility probe

Last checked: 2026-08-15

## Purpose

The `0455` harness proved stock USB and command `0x0d`, but its marker became
ineffective after complete stock initialization. This narrower `0456` probe
boots stock without touching persistent storage. Only explicit vendor command
`0x0e` performs the live-proven erase and marker writes, waits for completion,
then returns normally to initialized stock firmware.

This tests whether the marker operation itself disrupts wired movement,
scrolling, buttons, or USB after initialization. It does not yet enter custom
code automatically.

## Verified offline

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Linked injection | 340 | `6d9988870062ce4d961ed88f92820ba63cca49dfa96196347a69e1b98d62b87a` |
| Full container | 128,112 | `76669e150983725954fec510eb0c6717f84e08ef2a1a8ef3fb59cb49f7566905` |
| Updater payload | 119,920 | `5131a96feeab48e5b492034ac436b0bb8c2996642eb8032a957aed273177573e` |

Payload CRC is `f3cef231`; proposed USB `bcdDevice` is `0456`. The exact base
is the live-tested v4.53 container SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`.

Reset branches through `0x22cc`, enters the no-marker Thumb wrapper at odd
address `0x2213`, and resumes stock at `0x2068`. Command `0x0e` reaches the
late marker at `0x21be`. The verifier requires those distinct paths, exact
marker/storage literals, the 12-byte zero gap before the trampoline, unchanged
stock dispatch and IRQ/FIQ bytes, valid headers, exact ELF sections, and the
locked code/container identities. All current negative tests pass.

`cargo xtask late-marker-probe` builds and audits the artifact without hardware
access. The host command `set-late-marker --confirm` refuses any application
other than `047d:80d7`, `bcdDevice 0456`, and requires a valid command `0x0e`,
status `01` response.

## Proposed live sequence

1. Flash only the exact `0456` container and confirm stock USB and wired input.
2. Send `set-late-marker --confirm`; require the normal response.
3. Reconfirm movement, scrolling, buttons, USB identity, and stock command
   `0x0d` availability while the marker is present.
4. Reflash the same image, set the marker again, then remove USB power. Require
   resident loader `25a7:fabe` and query `d2`.

The second flash separates the software-recovery check from the cold-boot
fallback check.

## Verified live

On 2026-08-15, step 1 passed. The resident loader accepted all 3,748 payload
blocks from the exact locked container, and the application re-enumerated as
`047d:80d7`, `bcdDevice 0456`, with a 170-byte report descriptor. The user
confirmed ball movement, scrolling, and buttons behaved normally. The marker
was not set during this stage.

Step 2 then passed: the exact `0456` application acknowledged vendor command
`0x0e` with status `01`, and remained enumerated as `047d:80d7`, `bcdDevice
0456`, with the same 170-byte report descriptor. The user confirmed ball
movement, scrolling, and buttons still worked with the marker present.
USB-triggered recovery then passed: stock command `0x0d` reached resident
loader `25a7:fabe`, whose query response was `d2`.

For the isolated cold-boot test, the exact locked `0456` image was reflashed,
all 3,748 blocks were echoed, and command `0x0e` again returned status `01`.
With the battery disconnected, USB power was removed for at least five seconds
and restored. Without an application USB command, the device enumerated
directly as resident loader `25a7:fabe` and returned query response `d2`.
Cold-boot fallback therefore passed.

## Later architecture

After this compatibility gate, an experiment-entry probe will write the marker
and enter deliberately hanging custom code without returning to stock. Once
that cold-boot recovery passes, the development image can write the marker
automatically at a verified post-initialization hook before every custom-code
iteration. USB command `0x0d` remains the primary loader interface; power-cycle
marker recovery remains independent fallback.
