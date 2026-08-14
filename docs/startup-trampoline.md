# Startup trampoline

Last checked: 2026-08-14

## Purpose

This `4.53` image derives only from the live-proven `4.52` reset trampoline. It incrementally tests the standalone stub's remaining early startup assumptions while retaining stock firmware and all carrier recovery commands.

On every reset, before stock startup, its 60 bytes:

1. save the incoming CPSR and stack pointer;
2. enter supervisor mode with IRQ/FIQ disabled, matching standalone `mov r0,#0xd3; msr cpsr_c,r0`;
3. load standalone stack top `0x00407f00`;
4. branch ARM → Thumb through odd address `0x22e9`;
5. branch Thumb → ARM through even address `0x22d0`;
6. restore the incoming CPSR and stack pointer;
7. replay stock `mov r0,#0` and branch back to stock `0x2068`.

There is no trigger button and no bypass: this code runs unconditionally. If it fails before returning to stock, application USB and carrier command `0x0d` will not become available.

## Offline result

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Startup code | 60 | `0e24e9ffbf218afabde39043b177f19e29761b3175b772351fb6f7a839a800f7` |
| Full container | 128,112 | `dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b` |
| Transmitted payload | 119,920 | `da04628aa7e05ee253b63a4984b2ceb138d91029f239f11efd6914b0da9afc8a` |

Updater payload CRC is `4e9c5e53`; USB `bcdDevice` is `4.53`. The verifier requires exact v4.52 and standalone-stub hashes, checks every state/interworking instruction and literal, independently decodes the stock return branch, requires valid image CRCs, preserves the stock IRQ boundary, and rejects corruption.

The first draft accidentally applied the Thumb low bit twice, producing even pointer `0x22ea`. Disassembly caught it before hash locking or hardware access. The corrected pointer is odd `0x22e9`.

No startup-trampoline image has been sent to hardware. Passing this test would reduce the standalone risk further, but it cannot make the device unbrickable: a failure in this unconditional early path could still leave the intact resident loader unreachable over USB.
