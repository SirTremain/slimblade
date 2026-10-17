# Rea integration stage 1

2026-10-17. Scope: coordinator-only offline analysis integration, no firmware
worker assignment. No hardware, compiler invocation, queue transitions, commits
or pushes were performed for this integration. Existing compiler/profile/packet
pins and budget controls were not changed.

## Outcome

The unmodified Rea 6.5.0 Java bridge works against a checked disposable copy of
the corrected `SlimBlade-v449-runtime-v4` project. The adapter does not use
Rea's generic raw ARM import, install global skills, register MCP, launch model
jobs or represent local JSON as upstream canonical Evidence.

See [usage and boundaries](../../../docs/rea.md), the
[separate integration configuration](../../rea/config.json), and the executable
[real-control tests](../../../tests/test_rea_bridge_integration.py). Archive
acquisition provenance and exact local dependency identities are recorded in
the configuration and retained run reports. The selected archive's MIT licence
is retained alongside the unmodified Java sources in ignored local storage.
Exact identities of the final positive/negative reports are in
[reports.json](reports.json); paths there are relative to the repository root.

## Positive control

Final full-suite run retained:
`.decomp/rea/runs/control-test_positive_corrected_project-c99ced0a/`.

- Checked all 128112 mapped baseline bytes against
  `e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.
- Confirmed Ghidra 12.1.4, `ARM:LE:32:v5t`, the saved names/ranges/entry modes
  of all 776 inventory functions, the exact runtime call-fixup XML, inline data
  at `0x1e364`/`0x1e480`, absent false fallthroughs and zero saved error bookmarks.
  This is preservation checking, not approval of every discovered function.
- Collected 15 complete observations: instruction text, function dossiers and
  outgoing references for `0xbe60`, `0x112b0`, `0x1e4f0`, `0x1e150`, `0x1e420`.
- Checked the `0xbe60` instruction sequence and retained runtime injection
  warnings in the two repaired callers' pseudocode. The post-query admission
  result equals the pre-query result; source project content hashes are unchanged.
- Read retained summary/assembly views without starting another analysis.

## Negative controls and regression tests

Both controls alter only disposable admission expectations through the test
harness; neither changes the real firmware, runtime model or configuration pins:

- `.decomp/rea/runs/control-test_wrong_baseline-08fd398b/`: wrong expected SHA
  rejected with `database bytes differ from baseline`.
- `.decomp/rea/runs/control-test_wrong_runtime_model-27e761da/`: wrong expected
  XML rejected with `runtime model changed`.

Both report failure, zero returned observations and an unchanged original
project. The bridge also refuses the unprepared program after admission fails.

The complete suite with real Rea controls enabled passed **177 tests**. The
ordinary offline suite includes 20 new synthetic adapter tests; the three real
Ghidra tests require explicit opt-in and are skipped by default. Coverage includes
archive tampering, unwanted links, path escapes, changed local input pins,
method-specific RPC schemas, mutation rejection, malformed/oversized replies,
identity mismatches, deadlines/log limits, cleanup ordering and retained-result
tampering/caveat preservation. Existing local evidence/tool-lock checks pass.

During development, controls exposed and resolved sandbox owner/hostname lookup
requirements and differences between the three upstream parameter schemas.
Earlier failed runs remain ignored diagnostic evidence; they were not relabeled
as successful. Host account/DNS files were not mounted to fix those failures.

## Interpretation and next work

Rea adds useful call/reference, control-flow and value-flow context. It does not
independently recover the correct C ABI: `0xbe60` still appears as a no-argument
wrapper in pseudocode despite reviewed argument forwarding. Its caller coverage
is explicitly partial. Runtime helper pseudocode retains jumptable/register
uncertainties. These caveats remain in full observations and focused views.

The adapter's read-only request allowlist is distinct from the upstream bridge's
truthful mutable-capability advertisement. Only the isolated coordinator uses
the temporary socket, and only a disposable project copy is available to it.
This is not a security claim about arbitrary local same-user clients.

Next: use selected dossiers during new-batch boundary/dependency review, then
freeze new evidence packets through the existing intake. A separate worker run
still requires explicit scope, live quota and budget. No completed/blocked task
is reopened by this work. Full Rea MCP/provider/canonical-Evidence integration
is a later adaptation, not claimed complete. Matching coverage remains unknown;
full-image reconstruction and hardware gates remain outstanding.
