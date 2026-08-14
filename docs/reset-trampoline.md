# Reset trampoline

Last checked: 2026-08-14

## Purpose

This is the lowest-risk test of custom code at the earliest application entry point. It derives only from the live-proven recovery carrier and retains its stock mouse implementation and commands `0x0d`–`0x10`.

The stock reset vector still points to ARM address `0x2064`. That first instruction is replaced with a branch to `0x22b4`, where two ARM instructions replay the displaced stock `mov r0, #0` and branch back to `0x2068`. A normal `4.52` boot therefore proves the custom reset hook ran before stock startup.

## Offline result

The final container differs from carrier `4.51` at only 18 byte positions: eight regenerated header-CRC bytes, three non-identical bytes in the reset branch, six nonzero injected-code bytes, and the one-byte USB version. The other two injected bytes were already zero.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| ARM trampoline | 8 | `eb26dace22b23177e84b62225949e573cd2b2764add0a722411733f3cb2a57f2` |
| Full container | 128,112 | `bad4a3a7bdf3610e8b6cf0d9b1bb27f4d147ffa0efb242f24c0257bb454c6905` |
| Transmitted payload | 119,920 | `0bae1c229db988c03f6eb55b78a726d69fdf1f42048694a404335f00b950028a` |

Updater payload CRC is `db034cd6`; USB `bcdDevice` is `4.52`. Two forced builds produced the same hashes. [`tools/verify_reset_trampoline.py`](../tools/verify_reset_trampoline.py) decodes both branches, checks their absolute targets, requires the displaced instruction to equal stock, preserves the reset vector and IRQ code, checks the exact carrier base and output hashes, validates both image CRCs and rejects corruption.

The first draft used assembler syntax that treated `b 0x2068` as a relative displacement and would have targeted `0x4328`. Disassembly caught it before the image was hash-locked or sent. The final source uses explicit encoding `eaffff6a`, which the verifier independently decodes as `0x22b8 → 0x2068`.

## Live result

On 2026-08-14 the exact audited image was flashed through resident loader `25a7:fabe`. One attempt encountered the loader's periodic re-enumeration before the device was opened; it stopped before `B0` and therefore before erase. The retry queried BK3635 type `d2`, completed erase, received exact echoes for all 3,748 blocks, passed payload CRC `db034cd6`, and returned on the same USB path as `047d:80d7` with `bcdDevice 0452`.

Reaching the stock USB application after reset proves the patched branch at `0x2064`, both injected ARM instructions, and the return to stock `0x2068` all executed successfully. Both stock mouse and vendor HID interfaces enumerated with their expected descriptors. The user then confirmed normal movement, buttons, and scrolling.

The guarded USB utility accepts only the exact full-image and payload hashes above and requires the full container hash as confirmation.

## Remaining risk

The reset hook is now live-proven. The next standalone risk is the larger stub's CPU-mode setup, stack initialization, ARM-to-Thumb transition, and direct entry into the already-proven recovery routine.
