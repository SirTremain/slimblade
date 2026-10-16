# fn_00013f72 draft

The immutable packet's listing at `0x00013f72..0x00013f7a` decodes as
`strb r1,[r0]`; `lsr r1,r1,#8`; `strb r1,[r0,#1]`; `bx lr`. The source
expresses those two byte stores for a pointer and unsigned halfword. The
caller excerpts at `0x6930..0x693c` and `0x69b8..0x69d8` show a small immediate
or a value loaded with `ldrh` passed in `r1`, and a destination passed in `r0`.
This is consistent with the assigned signature but does not establish the
original declaration or qualifiers.

Ghidra's per-instruction state is Thumb at all four addresses. The independent
LLVM listing decodes the same bytes. The range has no calls, literal/data
references, stack use, or internal branch. The shift updates condition flags
in the machine code; the C expression does not promise flags, and those flags
are not part of the C ABI. Register clobbers beyond ABI-visible behavior and
the original source declaration remain review questions.

No compile or byte comparison was run: the enforced worker handoff assigns
compilation to the coordinator. This is a draft, not a verified match.
