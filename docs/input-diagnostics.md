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
report descriptor.

The marker-first capture then confirmed:

- signed combined X/Y motion at `0x00400192/194`;
- debounced/current button masks at `0x00400164/166`;
- processed/current button masks at `0x00400205/206`;
- physical button bits `01`, `02`, `04`, and `08`.

The per-sensor pairs remained zero because routine `0x1a74c` merges them into
the combined pair and immediately clears all four halfwords before an
asynchronous USB query can observe them.

## v4.67 sensor-shadow result

The stock instructions at `0x1a798` are replaced by one audited call. Before
the stock clear, it copies sensor A (`0x00400174/176`) and sensor B
(`0x004001da/1dc`) into the proven inactive buffer at `0x00401360`. It writes
only when either pair is nonzero, then replays the displaced B-X clear and
returns for the remaining stock clears.

Command `0x0e` first committed the persistent recovery marker and set volatile
byte `0x00401368` to one. Command `0x0f` returned the four signed shadow
halfwords.

- injection: 340 bytes, SHA-256
  `4e84e88d2c5342fd574f1c6c6da6cdfcd5a03e4a7b9f3919b792c4484541c908`
- container: 128112 bytes, SHA-256
  `b28a938e22ebf5b860cb9299f09317316ec15bed83e0874b98def81c8ca34f5c`
- payload SHA-256
  `4f6160983173d3c05ed5d0a20b548b513dd431bef4e23791ef8b8108477d5de4`
- payload CRC: `e67661e9`

The marker implementation, its storage literals, and the reset trampoline are
byte-identical to v4.64. Only the former mode-address literal at injection
offset `0xc4` is changed to the volatile shadow base; the marker starts at
offset `0x2c` but does not reference that literal.

The device enumerated normally and retained all stock input behavior, but a
15-second moving-ball capture returned only zero shadow values. The volatile
activation byte lies in a stock response workspace and is not stable across
the active loop, so it cannot guard the hook.

## v4.68 persistent-address activation result

The hook and stock patch remain at exactly the v4.67 addresses. Its eight-byte
guard now reads the first byte at persistent marker address `0x807c` and
activates only when it equals `0x12`, as written by the already proven
marker-first command. Relative to v4.67, only three injection bytes change;
the proven marker implementation, literal pool, reset trampoline, and sensor
helper remain byte-identical.

- injection: 340 bytes, SHA-256
  `c1fb7d21503eecd9aba0ab567289e1fde8f9687b518f96bdce59844388ae8eee`
- container: 128112 bytes, SHA-256
  `4b17aa182772c563a095261cd243d448c303d4ebb3d8a844def30d11ff0cf300`
- payload SHA-256
  `40fa8ca71b5a1dbaa1ac08983c9fc04ac46cc274faa09f7da5528a9e4049f732`
- payload CRC: `e1e8edbd`

The exact image flashed and retained stock USB and input operation. During a
properly coordinated moving-ball capture, all four shadow values still stayed
zero. Address `0x807c` is a storage-controller word address rather than a
direct CPU byte address containing `0x12`, so this guard remained dormant.

## v4.69 delayed single-query candidate

The firmware injection returns exactly to the audited v4.67 bytes. The host no
longer sends `0x0f` immediately after arming: it waits ten seconds without any
vendor query while the hook retains the last nonzero sample, then performs one
read. This matters because the `0x0f` response copy overlaps byte
`0x00401368`; polling at roughly 1 ms had cleared the volatile activation byte
before physical movement could reach the hook.

- injection: 340 bytes, SHA-256
  `4e84e88d2c5342fd574f1c6c6da6cdfcd5a03e4a7b9f3919b792c4484541c908`
- container: 128112 bytes, SHA-256
  `8e2e0649994561f4e37c4e33dae7764db483aaedd0d20a306229ea854ac28b39`
- payload SHA-256
  `06decfff4f7e74c89225bd5ef6148a6065f3d27aaaac4b133f25b9e5e4e9f507`
- payload CRC: `02f3599e`

The exact image flashed on 2026-08-16, returned as `047d:80d7` with
`bcdDevice 0469`, and retained its stock USB path. During an explicitly
coordinated ten-second moving-ball window, the single delayed query returned
sensor A `(1, 2)` and sensor B `(1, 2)`. This proves that the hook runs before
the stock clear and that both raw sensor pairs can be exported through the
stock vendor interface. The values are one captured instant, not calibrated
axis labels or motion totals.

## Remaining live questions

- Report byte 1 is the effective button mask.
- Report bytes 2 through 5 are signed X/Y motion accumulated from both optical
  sensors.
- Report bytes 6 through 9 contain wheel and other input/status fields.

Idle, individual-button, translation, and ball-rotation captures will label
the live fields before any sensor configuration or direct sensor-bus access is
attempted.
