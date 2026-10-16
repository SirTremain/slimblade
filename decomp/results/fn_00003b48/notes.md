# fn_00003b48 candidate

## Observed evidence

- Packet instructions at `0x3b48–0x3b62` show a Thumb leaf with no calls,
  global accesses, literals, or data. `0x3b4c` compares the first argument to
  `0xf0000000`; the equality branch at `0x3b4e` targets the zero return at
  `0x3b60`.
- On the non-sentinel path, `0x3b50` subtracts the second argument from the
  first, and `0x3b54` clears the top nibble. `0x3b58–0x3b5a` compares the
  result unsigned against `0x08000000`; `bcc` targets the zero return. The
  intervening block at `0x3b5c–0x3b5e` returns one.
- Coordinator feedback reports the previous candidate was 28/28 bytes with
  differences at `0x3b4e`, `0x3b5b`, `0x3b5c`, and `0x3b60`, described as
  branch/return-block layout.

## Candidate and inference

`fn_00003b48` preserves the sentinel return, unsigned modular subtraction,
mask, and unsigned threshold semantics. The threshold is expressed as the
positive `adjusted >= 0x08000000u` case returning one, followed by the default
zero return. This is intended to encourage the observed one-return block to
fall through before the zero-return block; compilation is pending, so this
layout inference is unverified.

## ABI and unresolved points

The packet signature is `unsigned int (unsigned int, unsigned int)` and the
entry is Thumb at `0x3b48`. Seventeen incoming call references are listed in
`/evidence/references.json`; that file provides call sites but no caller
prototype or independent type proof. The signature remains a hypothesis for
coordinator review. No boundary or shared-type change is proposed.

## Validation

- Read `AGENTS.md`, `docs/project-plan.md`, `docs/workflow.md`, `docs/pilot.md`,
  and the mounted packet instructions, disassembly and references.
- No compiler was run in the worker. The coordinator must compile this
  candidate using the pinned service and return redacted results.
- Requested model: `gpt-6-luna`. Elapsed time and cost are not available to
  this worker and are not asserted.
