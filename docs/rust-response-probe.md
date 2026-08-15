# Marker-first Rust response probe

Last checked: 2026-08-15

## Purpose

The `0458` probe is the smallest observable, returning Rust experiment. Stock
initialization and normal input run unchanged. Post-startup command `0x0e`
writes the proven persistent marker, calls a compiled Rust function that returns
`0x58`, stores that value in byte 3 of the stock vendor response, and returns to
stock USB processing.

Stock disassembly at `0x18f6e–0x18fd4` verifies that `r4` holds the 17-byte
response buffer, byte 3 is otherwise untouched, status byte 2 is written after
the carrier returns, and checksum byte 16 is recomputed. A valid response with
command `0x0e`, status `01`, signature `58`, and checksum `e6` is therefore an
observable Rust execution result.

## Verified offline

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Linked injection | 340 | `964b064a5ab6e5b3149caa3d002d12a04c2b7b37d5569ca058de7898bcdc573e` |
| Full container | 128,112 | `93e939ffdf19a7d862108182528fac7d9b066e59fa853b21327bedd6260b14d4` |
| Updater payload | 119,920 | `1b1a76c85e0a94345ff54c47389f93fd9038a1c23a9755ace956c87f907fd24b` |

Payload CRC is `671cf8a7`; USB `bcdDevice` is `0458`. The exact base is the
audited v4.53 container SHA-256
`dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b`.

The complete marker writer at injection offsets `0x22–0x113` is byte-identical
to live-tested `0456`. The eight-byte shim at `0x21c6` calls the Rust function
at `0x22c0`, stores its low byte at `[r4 + 3]`, and returns. The Rust function
is exactly `push; frame; movs r0,#0x58; pop`, occupies eight bytes, has no MMIO
or persistent-storage address, and leaves four bytes of the original gap zero.
The startup trampoline and stock IRQ/FIQ wrappers remain unchanged.

Only carrier commands `0x0d` and `0x0e` are active. Other routed values return
without storage or reset side effects. The verifier locks the dispatcher,
marker-before-call ordering, Thumb call target, response store, Rust bytes,
gap, ELF sections, container identities, and storage isolation. The full
`cargo xtask check` gate passes. No offline command accesses hardware.

## Proposed live sequence

1. From resident loader `25a7:fabe`/`d2`, flash only the exact locked `0458`
   container and require application `047d:80d7`, `bcdDevice 0458`.
2. Confirm movement, scrolling, and buttons before invoking Rust.
3. Send `run-rust-response --confirm`. Require command `0x0e`, status `01`,
   signature `58`, and a valid checksum.
4. Reconfirm movement, scrolling, and buttons after Rust returns.
5. Send stock command `0x0d` and require resident loader `25a7:fabe`/`d2`.

If Rust unexpectedly fails to return at step 3, the marker completed first;
remove USB power with the battery disconnected and require the same resident
loader.

## Verified live

On 2026-08-15, resident loader `25a7:fabe` returned `d2` and accepted all 3,748
blocks from the exact locked container. The application re-enumerated on the
same USB path as `047d:80d7`, `bcdDevice 0458`, with the unchanged 170-byte
report descriptor. The marker was not written and Rust was not invoked during
this stage. The user confirmed ball movement, scrolling, and buttons worked
normally. The Rust response remains open.

Command `run-rust-response` then returned a checksum-valid vendor report with
command `0x0e`, status `01`, and signature `58`. The application remained
enumerated as `047d:80d7`, `bcdDevice 0458`, with the same 170-byte descriptor.
This proves the marker routine returned, the compiled Rust function executed
and returned its signature, and stock response processing resumed. The user
confirmed ball movement, scrolling, and buttons still worked with the marker
present. Stock command `0x0d` then reached resident loader `25a7:fabe` at the
same USB path, and its read-only query returned `d2`. The proposed `0458` live
sequence is complete.
