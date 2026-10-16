# fn_0000e540 draft

## Observed facts

- At `0x0000e540`, `strb r1,[r0,#0]` stores the low byte through the pointer in
  `r0`.
- At `0x0000e542`, `lsr r1,r1,#8` shifts the incoming value right by eight;
  `0x0000e544` stores the result at `r0 + 1`.
- `0x0000e546` is `bx lr`. The complete owned range is `0x0000e540–0x0000e547`;
  there are no outgoing calls, literals, stack accesses or globals.
- Reviewed callers set `r0` to destination addresses and `r1` to halfword or
  small integer values. They do not use a return value. Examples include calls
  at `0x000044e2`, `0x0000690c` and `0x00008cea`.

## Candidate interpretation

The C writes the low then high byte of a 16-bit value using two byte stores.
`unsigned short` follows the locked signature hypothesis; the observed
right-shift/store behavior and caller `ldrh` values are consistent with that
width. `unsigned char *` models the two byte-addressed writes. This is a
behavioral interpretation; the original declaration and compiler provenance
are not known. The caller set is reviewed evidence, not proof against hidden
indirect callers.

## Validation and unresolved items

No compiler or comparison was run in the worker. Exact-range bytes and source/
ABI review remain pending coordinator review. The draft is not a verified
match, and matching coverage remains unknown. No shared changes are proposed.
