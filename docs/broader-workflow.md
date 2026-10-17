# Broader offline reconstruction workflow

Current handoff: [batch 4](batch-4.md). Batch 3 has finished with one reviewed
draft and one terminal blocked task; its manifest and startup prompt below are
historical preparation evidence, not instructions to reclaim those tasks.

Updated 2026-10-17. Both leaf batches are complete: ten reviewed drafts, not
certified matches. This preparation adds a reusable intake path beyond leaves;
it prepares batch 3 but does not start workers or implement full-image reconstruction.
The [preparation report](../decomp/results/broader-preparation/notes.md) records
real compiler controls and review. The gate selects only fn_0000be60 and
fn_000112b0; launch still requires committed preparation and a user-assigned run.

## Supported work and boundaries

| Work shape | Current handling |
| --- | --- |
| Contiguous Thumb leaves, no external data | Existing immutable ARMCC5 leaf comparator; unchanged pins |
| Contiguous Thumb bodies with ordinary direct BL calls | Separately pinned call comparator, fixed Thumb external symbols, exact relocation/target/load-byte checks; explicit callee ABI/effects review required |
| Globals/literal ownership, ARM/Thumb interworking, veneers, shared tails, indirect calls, interrupts/MMIO | Not admitted by the current comparators; evidence/ownership and new verifier qualification required |
| Complete image, metadata, startup data, packaging | Accounted for in the ledger, but not yet source-built or independently certified |

Call qualification used two small stock wrappers, ordinary C and unchanged
compiler options. Both reproduced their original ten-byte bodies and fresh
unchanged rebuilds; changed return values and omitted calls failed. Ten existing
leaves also rebuilt unchanged. This supports the tested call shape, not arbitrary
stock functions. The calibration specimens are **not queued worker tasks** and
their already-derived C must not be presented as fresh worker discoveries.

`armcc_calls.py` retains its historical `armcc5-direct-call-experiment-v1` scope
name and frozen bytes. The coordinator now understands that format; registration
alone does not grant task admission. Old experiment task hashes are proposal
hashes, **not** runnable assignment hashes. A new assignment needs its own full
definition, packet and new lock; never overwrite the existing experiment lock.

## Dependency and byte accounting

[reconstruction.json](../decomp/reconstruction.json) partitions every byte of the
128112-byte selected container, including prefix, metadata, mixed code/data,
startup data and trailer. The read-only accounting command checks gaps, overlap,
bounds and baseline identity, and reports declared/reviewed source bytes separately:

```sh
python3 tools/reconstruction.py
```

The current 194 declared function bytes and 127918 unassigned container bytes
are bookkeeping, not a matching percentage. All region reconstruction remains
unresolved. Only 174 bytes have reviewed source. Reviewed-source counts require the integrated report hash and source
hash to agree with the queue; stale integrations are flagged. Matching coverage
remains unknown. External storage is a separate dependency question, not permission
to remove container bytes from the denominator.

Two kinds of dependency must remain separate:

- `depends_on` is a scheduling dependency. Bootstrap tasks must be accepted;
  function prerequisites must be reviewed. Neither state certifies machine code.
- A call contract is a binary/ABI dependency. Fixed symbols identify callee entry
  addresses, never supply recovered callee implementations. Record arguments,
  return use, actual register clobbers and memory effects with addressed evidence.
  Global/literal callees remain in the unresolved dependency ledger even when a
  wrapper can be compared independently.

Do not put mutually recursive machine calls into an acyclic scheduling graph.
Review their contracts as a group and track unresolved implementation dependencies
separately. Shared headers/data require one coordinator-owned definition and byte
ownership plan; workers only propose changes in their results.

## Preparing the next batch

1. Select a small set supported by a qualified comparator. Review original bytes,
   exact ownership/boundaries, instruction state, callers, callees, access widths,
   aliasing and clobbers. Ghidra discovery is not approval of the full inventory.
2. Export immutable packets under `.decomp/evidence/`. Keep code bytes, listings
   and vendor binaries ignored. Include baseline/tool/source provenance, metadata,
   listing, caller/callee context and uncertainty. Do not mount compiler/private
   state or another task's outputs into workers.
3. Write ordinary function task definitions using the existing schema. Call-bearing
   definitions additionally include `calls` and `extern_functions`, as in the
   reviewed [call proposal](../decomp/proposals/direct-call-candidates.json).
   For each new lock, hash the **complete assignment excluding only `comparison`**
   with sorted, indented JSON plus newline into `task_sha256`. This binds packet,
   paths, signature, instructions and dependencies, not just the address.
4. Create a new immutable comparator manifest/lock, chained to the existing
   qualified parent for call tasks. Preserve old locks, expected bytes, flags and
   reviewed task definitions. Do not alter a boundary or comparator rule to improve
   output. Run local task/pin checks before any claim.
5. Fill [the batch template](../decomp/templates/batch.json), change its status only
   after review, and save it under `decomp/batches/`. Pin the complete task objects
   using the queue's compact canonical JSON hash, the reconstruction ledger and
   qualification reports and their profile locks. Local admission verifies that
   the selected verifier and parent profile equal the qualified profile, not
   merely that a report says passed. Every external callee needs exactly one complete
   contract linked to its container-address dependency. These two hash formats
   intentionally follow the existing comparator and queue contracts respectively.
6. Validate the frozen batch with `tools/reconstruction.py --batch <relative-path>
   --sha256 <digest> --local`. This is read-only; it does not activate, claim or
   launch anything. Its plan excludes reviewed/blocked/claimed tasks and reports
   unmet scheduling dependencies. Missing reports, pins or contracts fail closed.
7. Select it explicitly in the coordinator-owned policy with scope
   `reviewed-batch-v1` and `batch: {path, sha256}`. The preparation gate must carry
   that identical pin, exact member IDs, schema 1 and `ready: true`. Keep every
   existing quota/concurrency/time/attempt field unchanged. No window renewal is
   implied. Repeat offline tests and real controls for any verifier change.
8. Review and commit preparation before creating worker worktrees. Obtain a
   separate user-assigned run with explicit scope and budget. Check live quota,
   pause marker, runner versions, committed preparation, queue, source and local
   pins immediately before claims. A prepared manifest is not a model-job request.

The tracked template is intentionally incomplete and rejected by the validator.
The concrete [batch-3 manifest](../decomp/batches/batch-3-calls.json) is filled and
validated. It selects two new ten-byte bodies: fn_0000be60 forwards pointer/scalar
arguments to 0xbd7c then returns zero; fn_000112b0 passes zero to 0xe58c.
Those are addressed behavioral observations, not precomputed C. Their callee
implementations and transitive memory effects remain unresolved dependencies.

## Next run

First review and commit this preparation. No agent commit is made. Then assign
the bounded run below; the coordinator must still check the live quota/window,
pause marker, versions, queue, committed worktree and all local pins.

Read-only local batch preflight:

```sh
python3 tools/reconstruction.py --batch decomp/batches/batch-3-calls.json --sha256 9dc0b60e5914eb1b56e26a522587bb485198a879e8d9b917ff43a0c75f40b4de --local
```

Expected queue state is ten reviewed functions and two queued/unclaimed tasks.
The following block alone is the optional next-run prompt, not instructions
to launch during preparation:

```text
Create a Goal to coordinate batch 3 only: fn_0000be60 and fn_000112b0. Read AGENTS.md, docs/project-plan.md, docs/preparation.md, docs/broader-workflow.md, docs/swarm.md and decomp/prompts/coordinator.md. Verify committed preparation, frozen batch/ledger/profile/packet pins, queue, runner versions and live quota before claims. Use at most two gpt-6-luna workers through tools/swarm_worker.py, not inherited-permission subagents; gpt-6.1-sol only for a bounded escalation. Stop at 45% weekly usage remaining to preserve at least 40% for work. Fail closed on unavailable quota; honor PAUSED.json and ask before resuming or starting a new quota window. Use tools/swarm_build.py for serial pinned compilation and independent unchanged-source rebuilds. Audit every full diff and independently review source, ABI, aliasing, stack, argument forwarding, actual register clobbers and callee side effects. Fixed external symbols are not reconstructed callees; exact-range bytes are not certification. Respect the 20-minute, eight-attempt and three-no-improvement limits. Continue until these two tasks are reviewed or evidence-backed blocked, or the reserve guard stops the run. Record blocked reports with the terminal block review decision. Do not reclaim completed tasks, add tasks, broaden verifier scope, change pins, access hardware, commit or push.
```

The prompt ends above. No broader or automatically renewed run is implied.

## Running and finishing bounded work

The [existing runner](swarm.md) still owns isolation and quota supervision.
Use only `tools/swarm_worker.py`, at most two Luna workers; bounded escalation
requires the assigned run's budget. `tools/swarm_build.py` dispatches only trusted
leaf/call modules, serializes compilation, preserves attempt ledgers and requires
fresh unchanged-source review builds. Workers cannot choose commands or compiler
modules. Keep 20 minutes, eight attempts, three non-improving attempts, the 45%
weekly stop and explicit resume/new-window rules.

Audit every complete diff and source/ABI separately from exact bytes. Submit only
draft or blocked reports. Accepting a draft records `reviewed`, never `matched`.
An evidence-backed blocked report now has a terminal coordinator review decision
`block`; it stays blocked and cannot be silently reclaimed or released. Preserve
the claim/attempt history. A later reassignment needs explicit scope/budget and a
deliberate coordinator reconciliation, not a fresh worker ID to reset limits.

## Whole-image and hardware gates remain closed

This workflow must eventually grow ownership/mapping support for code, shared
data, literals, startup/interrupts, metadata and packaging. Require negative
controls for every new shape, a clean independent source build, a complete byte
and SHA-256 comparison, and dependency/storage review before certification.
Concatenating exact leaf fragments with original unknown bytes would not be a
reconstruction. The [project plan](project-plan.md) remains authoritative for
replacement-device compatibility, backups, recovery and separately requested
flashing. No current preparation result establishes safe flashing.
