# Bounded free-toolchain investigation — 2026-10-16

User requested concrete progress rather than further licensing discussion.
This is coordinator preparation, not a paid worker run or a firmware release.

Predeclared hypotheses, before executing the new comparisons:

1. Four pilot utilities correspond to `co_read16p`, `co_read32p`,
   `co_write16p`, `co_write32p` in the historically preserved SDK `co_utils.h`.
   Compile their unaltered bodies with external linkage for measurement. Preserve
   the SDK's forced-inline 16-bit helper inside its 32-bit reader. Keep the two
   existing clock hypotheses unchanged; their source correspondence is unknown.
2. SDK mouse Makefile settings (`-Os`, ARM968E-S, Thumb/interworking, section
   splitting, GNU inline semantics, fast math) are a stronger configuration lead
   than arbitrary flag search. First test without LTO to isolate source effects;
   then test its documented LTO mode. No automatic search or per-function flags.
3. The SDK's explicit `armgcc_4_8` support directory warrants one GCC 4.8 release
   comparison against the already tested GCC 4.9.3. It is a version-family lead,
   not a proof of a particular release used by Kensington.

Order: GCC 4.9.3 SDK source/no LTO; GCC 4.9.3 SDK source/LTO; GCC 4.8 SDK
source/no LTO. At most three additional compile/diff iterations per function;
stop this experiment afterwards, even if no configuration matches. Use the
existing exact ranges and comparator unchanged. A few exact leaves do not
certify a compiler, runtime, ABI or whole firmware. Preserve every mismatch.

The four SDK bodies and source snapshots remain ignored local research evidence,
not submitted recovered C. Do not force registers, add assembly or alter the
oracle/boundaries to make outputs match. No queue/task/toolchain-lock edits.

Also inspect the SDK's prebuilt stack metadata if available through its recorded
public upstream revision. Static analysis only: no SDK Makefile, updater,
installer or device tool is executed. Record failed retrievals explicitly.

## Follow-up SDK control, after the three stock comparisons stopped

The downloaded, pinned SDK ELF records GCC 9.2.1 20191025 in `.comment`.
This is new evidence about that SDK artifact, not Kensington's compiler.
Download the corresponding official native Linux release and run **one**
separate SDK-only control: a two-null-pointer list initializer, using the
SDK header's non-profiling list layout, against the ELF's sized `co_list_init`
symbol. Its body is a simple contract hypothesis, not supplied SDK source.
No tuning, retries or reopening the six stopped stock-function attempts.
This establishes native ARM9 tool execution and tests one known-version SDK
example. It does not establish stock compiler compatibility or open the gate.
