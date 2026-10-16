# Second preparation pass — 2026-10-16 UTC / 2026-10-17 Brisbane

Starting commit: `c319429` (`feat: 6 functions down`), clean main worktree.
The prior six drafts were committed by the user, remain queue-reviewed, and
retain their original definitions, source files, reports, evidence and locks.
No commit, push, firmware worker or hardware operation was performed in this pass.

## Four-leaf readiness decision

The four assignments listed in [the batch-2 handoff](../../../docs/expansion.md)
have reviewed contiguous Thumb bodies and total 76 owned bytes. Fresh Ghidra
export used `-readOnly -noanalysis` on `SlimBlade-v449-runtime-v4`, preserving
the saved database. It checked the entire container hash, each function body,
per-instruction TMode, instruction lengths and local analysis-error absence.
[prepare_next_batch.py](../../../tools/prepare_next_batch.py) then verified the
frozen inventory/evidence packet, unique range ownership, original bytes,
control flow, entry-only known references, callers and independent LLVM decode.
The packet omits pseudocode and recovered C.

Review observations:

- `0x13f58`: six alternating reads/writes at offsets 0..5. Known callers
  `0x4ff2` and `0x55e6` ignore a return. Do not assume non-overlap or introduce
  restrict, bulk loads, or a memcpy call.
- `0x13f72`: six discovered callers supply immediates or halfword values and
  do not consume a result. This supports, but does not prove, the pinned
  unsigned-short/void hypothesis.
- `0x154d4`: eight known callers store the complete r0 result. Several keep
  r3 live across the call; the exact leaf preserves it. An AAPCS-compatible
  rewrite that clobbers r3 is not adequate. Preserve byte accesses and inspect
  the emitted instruction effects independently.
- `0x18100`: known callers `0x175d4` and `0x177fe` test the zero/one result.
  The r1 threshold comparison is unsigned. Semantic names and the original
  declaration are unknown.

The new lock uses the unchanged ARMCC5/LLD flags, source policy and comparator.
These are new leaf assignments, not pre-decompiled or already matching source.
The four exact proposal definitions are now in the main task inventory.
The active preparation gate selects only those four; the bounded runner now
checks an explicit batch allowlist before either launch or build. Old tasks
remain reviewed, not requeued. No claim or model budget was started.

## Direct-call experiment and compiler controls

[armcc_calls.py](../../../tools/armcc_calls.py) adds a separate lock chained to
the prior leaf lock. It binds external Thumb symbol addresses without dummy
implementations, validates prototype hypotheses, rejects indirect calls and
external data, checks relocation symbols/addends and verifies final BL targets
and all load bytes. No existing pinned comparator file was edited.

The two wrapper bodies `0x6464..0x646e` and `0x6500..0x650a` passed original-byte,
Ghidra-state, boundary, caller/reference and LLVM checks. Their call targets are
`0x1291c` and `0x134d4`. Those callees touch `0x401624` and `0x400501`, respectively;
their implementation and storage ownership are outside the experiment. Both
wrapper return declarations are hypotheses because known callers ignore r0.
No C candidate for either stock wrapper was compiled in this preparation.

Real compiler control run `.decomp/call-controls-v2/` passed 11 checks:

- Synthetic two-call source builds successfully and its unchanged fresh rebuild
  reproduces every load byte.
- Changing a callee, changing an argument, and removing a call each changes the
  compared bytes and fails equality; no relocation bytes are excluded.
- All six prior reviewed sources rebuilt unchanged through the original pinned
  leaf path, reproducing all 98 owned bytes.

The earlier `.decomp/call-controls-v1/` is retained as a failed control:
compilation/linking succeeded, but the new object check initially rejected
ARMCC's `STV_HIDDEN` extern functions. The unfrozen experiment was corrected to
accept only default/hidden visibility with the already restricted symbol
binding/target. Tests retain rejection of weak, internal/protected and other
visibility bits. No stock expected bytes, flags or prior lock changed.

The offline tests also exercise malformed/truncated objects, wrong relocation
types/symbols, offcut addends, extra allocation, altered linked targets,
prototype changes, assembly, indirect calls, global/static state, lock drift
and strict batch exclusion. Real mount-isolation tests include the additional
read-only handoff document. No paid synthetic model smoke was needed: the CLI
command and permission configuration did not change.

Final verification: all **136 offline tests passed**, including real outer and
inner sandbox-isolation checks. Existing SQLite ResourceWarnings remain in the
test harness; no tests failed. Full local preflight reports 13 valid tasks
(three bootstrap, six reviewed, four queued), with every local tool/evidence
lock verified. Runner versions still match Codex CLI 0.162.1 and bubblewrap
0.13.1. The six original definitions and source files compare unchanged against
the starting commit. Changed-document relative links and `git diff --check`
pass. The final live reading was 79% remaining in the same weekly window.

## Artifact identities

All binary/listing/packet/build artifacts remain ignored. The baseline source
URL, retrieval date, length and hashes remain in
[baseline.json](../../baseline.json) and its acquisition records; no vendor
artifact was downloaded in this pass. The original container is 128,112 bytes,
SHA-256 `e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Prior `.decomp/pilot-armcc5-v1/lock.json` | unchanged | `2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a` |
| `.decomp/next-batch-export-v1.json` | 11829 | `94634648ce453c4fe8cbe571e000512acc8df2a7727d59b95bad2deb7e3aff39` |
| `.decomp/next-leaves-v1/lock.json` | 10789 | `0b97891fa61305778b4ceceaaf8cc30e4070376f8b3f63debb79dd3591a77b33` |
| `.decomp/next-leaves-v1/functions.json` | 7074 | `ea307473b1e79d07f968a8832f4295b0227cc175872623a5a14885188b5f16d2` |
| Active `.decomp/next-leaves-v2/lock.json` | 10789 | `282c4bd898a44217d491dceef956452aee8f0eabba834b5c85f36ec87c92f76b` |
| Active `.decomp/next-leaves-v2/functions.json` | 7074 | `557e52013733e7768f39199ab066b81385770fb0bb7da7650b77543ed085d740` |
| `.decomp/direct-calls-v1/lock.json` | 3530 | `973b9272d7345924e44b5084437b05557e18731afbcea257fee37b593ac1c3bc` |
| `.decomp/direct-calls-v1/report.json` | 1452 | `f12f26af50f5b92d715e3cf7c3668e490a23e603ddbd90693ce351530b1ef2be` |
| `.decomp/call-controls-v2/report.json` | 7121 | `57ef9e6f0991f748a90c1bf1e76bd5b774fb96214e74cca30f394b788399dc70` |

The initial unassigned leaf proposal (`next-leaves-v1`) stored packets beneath
its own output folder. Full queue preflight correctly rejected that path:
packets must be beneath `.decomp/evidence/`. The generator was corrected and a
fresh v2 proposal/lock was created, preserving v1. No v1 task was ever claimed
or entered in the queue. The active v2 packets live in
`.decomp/evidence/next-leaves-v2/`; their contents, ranges and flags are unchanged.
A regression test now checks actual public task definitions against the queue
schema, gate, proposal and runner allowlist without needing private artifacts.

Compiler-control supervision recorded 79% weekly quota remaining throughout,
with the existing reset timestamp `1792649638`. No pause latch was cleared and
no new quota window was assigned. The 45% stop, 40% reserve, two-worker ceiling,
serial compilation and cumulative task limits are unchanged.

The OpenAI Docs review reaffirmed explicit permissions and isolated
[non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode).
Only batch membership checks and one read-only instruction mount were added;
no authentication, model selection, network or writable-mount permissions were
broadened. The [Arm ELF ABI](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst)
was consulted for Thumb BL relocation semantics. Both pages were checked
2026-10-16; local tests establish the behavior of this installed toolchain.

## Handoff

Next: commit preparation, then explicitly assign the four-task run using the
prompt in [expansion.md](../../../docs/expansion.md). Recheck pins, versions,
live quota and PAUSED.json immediately before claims. Worktrees must start from
the preparation commit. The direct-call prototype is deliberately not registered
as a queue comparator and both wrapper candidates are excluded from the runner.
They still need stock qualification and guarded build integration. Shared data
and whole-image verification are later work. Matching coverage remains unknown;
none of these checks establish safe flashing or replacement-device compatibility.
