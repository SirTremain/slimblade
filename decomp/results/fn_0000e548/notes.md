# fn_0000e548 draft

## Observations

- The assigned range is Thumb code at `0x0000e548..0x0000e558` (16 bytes),
  SHA-256 `04e53681093316a093f0ac635bc4d05dbe612bfe3e77f87d74fb5b3edafa124e`.
- At `0xe548`, `lsr r2,r1,#8` precedes byte stores at offsets 0 and 1
  (`0xe54a`, `0xe54c`). Shifts by 16 and 24 occur at `0xe54e` and `0xe550`;
  stores at offsets 2 and 3 follow at `0xe552` and `0xe554`. `bx lr` ends the
  body at `0xe556`.
- The Ghidra-exported packet and independent LLVM listing agree on all eight
  instruction encodings/semantics. There are no calls, literal/data ranges,
  absolute globals, stack accesses or MMIO constants in the body.
- The two recorded call sites are `0xbd5c` and `0xc89a`. Their setup loads a
  32-bit value into `r1` and a writable address into `r0`; neither consumes a
  return value. No call-site evidence contradicts the proposed two-argument
  AAPCS signature.
- The code performs four ordered low-byte stores of successive 8-bit slices of
  the input value. Explicit casts keep the narrowing at each byte store clear.

## Inferences and open questions

- `unsigned int` is consistent with the 32-bit ARM register operations and
  pinned signature hypothesis. The exact original source declaration,
  qualifiers, compiler provenance and ABI are not established by instruction
  bytes. `unsigned char *` is consistent with `STRB`; aliasing and pointer
  validity preconditions are unknown.
- Reference discovery reports only entry references; it cannot rule out an
  undiscovered indirect caller.

## Provenance and validation

- Baseline: `slimblade-pro-stock-v4.49`, 128112 bytes,
  SHA-256 `e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.
- Artifact source URL: `https://accobrands.co.jp/wp/wp-content/uploads/Kensington-Slimblade-Pro-V4.49.zip`;
  retrieval/inspection date recorded in packet metadata: `2026-10-16`.
- Evidence packet hash from assignment: `b5078bc799ad66c5dd2001c2685ed352b660211d6e7feed21791c21cb6749752`.
- No compiler/comparison command was run by this worker. Exact-range bytes and
  source/ABI remain unverified; request coordinator compilation and review.
