# Independent comparison prototype — 2026-10-16

The synthetic compile/link/compare workflow is implemented and tested. It
cannot certify stock firmware matches; the original compiler is still unknown.
No firmware functions were reconstructed. The prototype intentionally stays
under this task's result directory instead of being presented as a production
matching verifier in `tools/decomp.py`.

## Reproduce the suite

Clang, LLD and llvm-objcopy must already be on PATH. This session used 23.1.1.
The implementation uses Python's standard library. Use a fresh output directory.

```sh
python3 decomp/results/bootstrap-verifier/selftest.py .decomp/verifier/suite-v2
```

The command creates a coordinator-owned reference from the supplied synthetic
C, freezes the reference ELF and linker script, then invokes the verifier in a
separate process for each candidate. It never uses a candidate's supplied object
or executable. `init-synthetic` refuses an existing oracle, and each candidate
build requires a new output directory. Expected output is never refreshed by
candidate verification.

The observed run passed **21 checks**, with two successful independent builds.
Rejected controls cover wrong constants, signed byte loads, missing volatile
stores, changed call targets, changed read-only data, initialized data, BSS
extent, function prototypes, inline assembly, executable byte arrays, function
pointer casts, prebuilt output, damaged oracle bytes, changed flags, changed
linker script, changed compiler hash and an unknown toolchain. Two additional
checks establish that the large constant lives in a literal pool and that the
call control's object `.text` bytes are identical before relocation while the
linked call target differs and is rejected.

An initial test used a signed-char *parameter*. Changing its signedness produced
identical instructions because AAPCS puts narrow-argument extension on the
caller. That test correctly exposed the limits of byte comparison. The final
fixture tests a signed-byte *load*, and the verifier also pins function interface
types to reject ABI changes that need not change callee bytes. The failed first
suite is retained locally as `suite-v1`; the new synthetic fixture was frozen
in a separate oracle. No stock expected bytes, compiler flags or boundaries
were adjusted to obtain a match.

## What is pinned and compared

[synthetic-lock.json](synthetic-lock.json) records the observed reference lock:
SHA-256 `ee9aac190057fb65face3639fb1f69c1b2a9c55e1d5b405499ac648826133520`.
It covers compiler/linker executables and reported versions, their resolved
shared libraries, Python executable/version, verifier source hash, reference C,
reference ELF, linker script, function interfaces, flags, ABI and build environment.
The expected lock hash is supplied separately to verification; editing a lock
does not silently bless modified flags or reference bytes.

The fixture uses Thumb ARMv5TE, ARM968E-S, AAPCS, soft-float, `-O2`, no LTO,
no standard includes and no runtime libraries. These are synthetic settings,
not guesses recorded as stock settings. Code starts at `0x1000`, read-only data
at `0x2000`, initialized data at `0x3000`, BSS at `0x4000`; external Thumb
symbols are fixed at `0x9001` and `0x9101`. No stub implementations stand in for
those symbols, and execution is not attempted.

Comparison includes every allocated ELF section's address, size, flags,
alignment and bytes; NOBITS sizes; ELF entry/state and flags; and every PT_LOAD
segment's virtual/physical address, file/memory size, flags, alignment and full
file bytes, including padding. It does not mask relocation slots. Relocations
remaining in the final ELF are rejected. Non-allocated debug/symbol/string
tables are not runtime bytes and are excluded. This scope is not a Kensington
container serializer or whole-stock-image comparison.

To verify the supplied reference against this session's pinned local oracle,
use a fresh output directory:

```sh
python3 decomp/results/bootstrap-verifier/verify.py verify-synthetic .decomp/verifier/suite-v2/oracle ee9aac190057fb65face3639fb1f69c1b2a9c55e1d5b405499ac648826133520 decomp/results/bootstrap-verifier/reference.c .decomp/verifier/recheck-build
```

The accepted reference ELF hash was
`d26e445b7ebd3e73080523f77f346705c846fee7820b1ed1eaafad2cc6d66dbd`.
The local suite report `.decomp/verifier/suite-v2/results.json` has SHA-256
`febd7796d01b31eb65c062faf688fab40ea48cef06ff43186214f7d997fac6b8`.

## Limits before production integration

The oracle is outside candidate build directories and marked read-only, but
same-UID processes can change permissions. This is not a hostile-worker sandbox
or protection against concurrent tampering. Production integration needs an
enforced read-only oracle/tool environment, a separate verifier process/account
boundary, and full allowed-path diff review. Python's standard-library files,
kernel and full OS filesystem are not frozen; package updates fail executable
or shared-library pins but this is not a hermetic environment image.

The restricted source checks reject directives, assembly, attributes and
function-pointer casts. They are useful controls, not a general proof that
arbitrary C represents recovered behavior. Human review must detect disguised
byte encodings, omitted behavior, dead code, undefined behavior and stubs.
Exact machine bytes alone do not establish correct source types or semantics.
The fixture is not executed, so the suite proves comparison behavior, not an
ARM semantic model.

Before any stock match claim, identify and pin a legitimate historical compiler,
ABI, libraries, flags and linker; independently approve evidence and ownership
for every function/data range; account for veneers, literals and shared tails;
build the real container without copied code blobs or post-link instruction
patching; compare its complete hash; and rerun all accepted matches on each
integration. None of those stock-certification gates is claimed complete here.
