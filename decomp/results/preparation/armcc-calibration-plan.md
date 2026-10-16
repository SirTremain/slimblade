# ARMCC5 calibration continuation — 2026-10-16

The user requested continuation after the Professional-key headless smoke test.
Use the existing local ARMCC 5.06u7 b960 and installed license; no new activation,
download, hardware operation, worker launch or paid job is part of this task.

First experiment: all six unchanged hypotheses and ranges in `calibrate.py`,
once each. Use `--cpu=5TE --thumb --apcs=/interwork --fpu=SoftVFP --littleend
--c99 --gnu -O2 -Ospace`. CPU replacement is prescribed by the bundled release
notes. Thumb is observed in the stock packets. C99/GNU/interworking/size preference
have related SDK project leads; O2 retains the successful smoke-test level and
is a candidate choice, not a decoded historical SDK setting or provenance claim.
Link with ARM's linker at the original address, no library scanning or unused
section removal. No expected bytes, boundaries or existing worker locks change.

Record failed builds as well as mismatches. Do not normalize or trim generated
padding, mask relocations, patch instructions, or tune source to improve a score.
If linker representation requires a format-specific reader, validate complete
allocated bytes/load mapping independently, including the two-byte entry.

Then test repeatability and deliberate wrong constants, signedness, stores,
literal data and trust inputs. The compiler sandbox receives sources/build
outputs, not the stock image or evidence oracle. Keep diagnostics redacted and
license material private. Synthetic and calibration outputs are not worker
submissions, matching certificates or a full-image build. The gate stays closed
until calibration and the selected integration have been reviewed.

## Documented linker-layout correction after the first run

The first batch (v2; v1 stopped before compilation) exposed integration defects:
the reader rejected Arm's `PF_ARM_ENTRY` segment bit, and the default linker
region alignment imposed four-byte bases/tail padding even on two-byte-aligned
Thumb input sections. No source mismatch diagnosis was made from those failures.

Use a separate v3 output with unchanged compiler flags/sources and the documented
`--no_legacyalign` option: natural region alignment follows its input sections.
This addresses the independently observed two-byte stock entry, not a change to
the oracle or a post-link padding trim. Accept exactly `PF_ARM_ENTRY | PF_R | PF_X`
for this Arm-linker reader, and continue checking every load byte and size.
References: [Arm linker alignment](https://documentation-service.arm.com/static/5eaada9d9931941038df982b),
[Arm program-header example](https://documentation-service.arm.com/static/65f99551b145b95232658cd9).
If v3 still cannot represent the original ranges, retain the failure rather than
changing the comparison boundaries. No optimization/source search is authorized.

## Leaf-linker isolation check

V3 still adds two trailing bytes to 10/22-byte objects and rejects the two-byte
load base. A separate synthetic scatter control (`probe`, address `0x1002`)
rejects explicit `ALIGN 2` with L6940E: regions require alignment at least four.
These are region-layout limitations, not missing compiler access or instruction
mismatches. Do not suppress diagnostics or trim the resulting load segments.

V4 keeps every source/compiler option unchanged and tests ARMCC objects through
the existing strict LLD per-leaf layout instead. That layout supports the original
two-byte entry and compares the full sole executable segment without padding
normalization. Explicitly discard ARMCC's non-allocated `.arm_vfe_header`
metadata alongside the existing non-runtime metadata. LLD is an isolated-leaf
relocation/layout tool here, not identified as the stock full-image linker.
Retain both failed Arm-linker variants. Full-image linking remains later work.

V4 correctly rejected unassigned non-allocated `.debug_frame` metadata under
the strict orphan policy. V5 explicitly places that debug section at address
zero outside runtime allocation; it does not suppress the orphan check or
discard/trim executable bytes. This is a linker-script integration correction,
not a source or optimization iteration. Repeat the six source builds once.
