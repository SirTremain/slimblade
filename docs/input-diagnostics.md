# Input diagnostics

## Verified static findings

- Stock routine `0x16838` samples five GPIO-derived button bits and debounces
  them through the structure at `0x00400160`.
- Stock routine `0x19ce8` compares the five-bit state at `0x00400164`, handles
  changed bits, and publishes a processed button byte at `0x00400205`.
- The wired loop copies `0x00400205` and the halfwords at `0x00400192` and
  `0x00400194` into stock input-report bytes 1 through 5 at `0x00401362`.
- The same report contains adjacent flags in bytes 6 through 9 and a checksum
  over bytes 0 through 14.

## v4.65 diagnostic candidate

Command `0x0e` first writes the persistent recovery marker and returns the
tested `a9` arm signature. Command `0x0f` then copies RAM
`0x00401360..0x0040136b` into vendor-response bytes 4 through 15. The Rust CLI
decodes these as two prefix bytes, sequence, buttons, signed X/Y motion, and
four adjacent report fields.

The query is read-only. It neither writes sensor registers nor changes mouse
reports. The CLI refuses to run it unless the device reports `bcdDevice=0465`
and explicitly writes the recovery marker before requesting the snapshot.

- injection: 340 bytes, SHA-256
  `b4bef493b1b5f2e49c5e880f307dad8c633e8d5b3e78849deb32ba7f26fc1928`
- container: 128112 bytes, SHA-256
  `4a90ccf453b80cbbf4018dfec87d14051dfff3ea076445822c28dfbc3e4f55a3`
- payload SHA-256
  `1c5854dc8b2e66a814a0dc5ebf41768a3ebcc58da83addbcb6b512b3090e6f59`
- payload CRC: `ef6ab24a`

The marker writer (`0x21d8..0x229f`) and reset trampoline
(`0x22cc..0x22ff`) are byte-identical to the live-tested v4.64 guard. Only the
old state-query stub, dispatcher wrapper, and former no-op experiment space
are repurposed.

## v4.65 live result

The device retained normal pointer, scrolling, and button behavior. An idle
snapshot and a 15-second capture during ball movement, rotation, and button
presses returned twelve zero bytes throughout. Therefore `0x00401360` is not a
usable live wired-mode source; it is either inactive or cleared before the
vendor command can observe it.

## v4.66 paged diagnostic candidate

Command `0x0f` now treats request byte 3 as a selector and returns twelve bytes
starting at `0x00400160 + selector * 8`. It also echoes the selector in response
byte 3 so the host rejects mismatched replies. The host capture cycles through:

- `0`: button debounce state at `0x00400160`;
- `2`: first per-sensor accumulator window at `0x00400170`;
- `6`: combined motion at `0x00400190`;
- `15`: second per-sensor accumulator window at `0x004001d8`;
- `20`: processed button/status state at `0x00400200`.

The eight-byte selector stride keeps every address word-aligned while the
twelve-byte reply covers both halfwords of each known accumulator pair.

- injection: 340 bytes, SHA-256
  `3e17a0b58cef059ace43d43bf4d957f65cf2ef29f14711ca0205e4a8e9e34a65`
- container: 128112 bytes, SHA-256
  `c5fb2b865c6ba1993c673f989e5c811bfa661b31f8c6261d2ab04e95eab5692f`
- payload SHA-256
  `6006faab993f9ba83b30a365376ad889dfcbf20af22de057e98d2c680516723d`
- payload CRC: `7ed63bf1`

The marker writer and reset trampoline remain byte-identical to the
live-tested v4.64 guard. The selector is bounded by the host to the five values
above; firmware accepts a byte and can address only the corresponding
eight-byte-stride RAM page.

The exact container was flashed on 2026-08-16. The resident loader answered
`d2`, all 3,748 payload blocks echoed, and the application returned on the same
physical USB path as `047d:80d7`, `bcdDevice=0466`, with the stock 170-byte
report descriptor. The marker-first capture command has not yet been sent.

## Remaining live questions

- Report byte 1 is the effective button mask.
- Report bytes 2 through 5 are signed X/Y motion accumulated from both optical
  sensors.
- Report bytes 6 through 9 contain wheel and other input/status fields.

Idle, individual-button, translation, and ball-rotation captures will label
the live fields before any sensor configuration or direct sensor-bus access is
attempted.
