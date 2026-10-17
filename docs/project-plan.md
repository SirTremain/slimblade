# Project plan

Updated 2026-10-16. This is the current project roadmap. [AGENTS.md](../AGENTS.md)
sets working rules; [workflow.md](workflow.md) describes task coordination.
Historical experiments, bootstrap reports and narrow task packets are evidence
or assignments, not competing project goals.

## Milestone 1: reconstruct, verify and test stock firmware

The first major milestone is a source-built version of official Kensington
firmware that matches its reference image exactly and has been flashed and
tested successfully on the replacement SlimBlade Pro. No OpenAxis changes
or feature removal belong in this milestone.

### 1. Reconstruct the official firmware

Decompile and reconstruct all code and data in the selected official image,
including wired USB, Bluetooth, 2.4 GHz, startup, interrupts and update/recovery
paths. Preserve stock behavior and original bugs during matching. Recover a
reproducible build, not just readable Ghidra pseudocode.

The currently verified analysis input is v4.49; it is not yet established as
the correct flashing target for the replacement device. Any different official
image needs a separate, recorded baseline. Never change expected bytes to make
a candidate pass.

### 2. Account for everything else required to run and recover it

Inventory dependencies beyond the updater's embedded application: resident
loader, ROM services, libraries, other firmware/storage, image metadata and
checksums, update transport, calibration, device identity and pairing state.
These are questions to resolve, not assertions that all are present or contained
in the updater package.

Analyze or decompile additional components where needed to establish correct
build, loading, operation and recovery. For each component, record its source,
identity, address/storage mapping, role and treatment: reconstructed, preserved
unchanged, immutable external dependency, or unresolved. Do not assume an SDK
for a related chip is equivalent, or claim preserved binaries as recovered C.
Unknown critical dependencies block hardware work.

Device-specific data must be preserved, not regenerated from another device's
dump. The complete selected firmware image still requires byte-by-byte
accounting; an explicitly external dependency does not justify excluding
difficult regions from its reconstruction denominator.

### 3. Independently verify an exact stock rebuild

Pin input hashes, compiler/linker versions, libraries, ABI, build flags, layout,
packaging and verifier revision. Build from a clean source checkout independently
of worker outputs. Compare the complete selected image byte-for-byte and by
SHA-256, including code, data, vectors, literals, metadata and padding. Also
identify exactly which ranges the updater transfers and where they go.

Function comparisons and negative controls support this process; similarity
scores, reviewed drafts and the synthetic verifier are not whole-image proof.
Record any necessary hand-written assembly separately from recovered C. Stubs,
embedded original instruction blobs and post-link patches must not masquerade
as reconstruction.

Acceptance requires a reproducible exact image, an explicit dependency/storage
account and an independently reviewed verifier. This establishes equivalence
to that reference image, not compatibility with every hardware revision or
zero risk when flashing.

### 4. Flash the verified stock rebuild and validate the device

Flashing and hardware validation are part of this milestone, but only after a
separately requested hardware session with these prerequisites documented:

- Identify the replacement device, hardware revision and installed firmware;
  establish compatibility with the chosen official reference.
- Record stock behavior before the write. Preserve required device-specific
  state and obtain verified backups of readable storage needed for recovery.
  If a region cannot be read, document the limitation and establish why the
  proposed operation does not endanger it; otherwise stop.
- Establish a recovery route that does not depend on the candidate application
  continuing to run. Do not infer this from an untouched marker writer, a
  related-chip SDK or the previous device's behavior.
- Review the update tool, image-to-flash mapping, exact target ranges, checks
  and power requirements. Do not overwrite the loader, calibration, identity
  or other regions merely because a container includes bytes at similar offsets.
- Present the exact image hash, target device, write method/ranges, recovery
  evidence and test/stop plan to the user before executing the hardware session.

Flash the independently rebuilt image, not a substituted vendor binary. Verify
programmed ranges through readback where supported; distinguish direct byte
verification from updater acknowledgements or successful enumeration. If the
verification method cannot establish what was written, record that gap rather
than declaring the hardware milestone complete.

Repeat the before/after functional checks: movement, buttons, scrolling, DPI,
wired USB, power cycling, reconnect and suspend/resume, plus stock Bluetooth,
2.4 GHz, pairing and power/battery behavior where present. Record expected and
observed results and any untested cases. An approved recovery check is separate
from the normal-boot test. Any failure blocks further experimental flashing.

Do not add a custom recovery marker to the exact-match stock artifact: that
would change its bytes. The [marker reachability requirement](marker-reachability-gate.md)
remains a release gate for the later modified firmware and must be evaluated
against the actual target, not copied from historical addresses.

Milestone 1 ends only after the exact rebuild, dependency/recovery review and
hardware verification pass. Decompilation reduces uncertainty; it cannot make
flashing risk-free.

## Milestone 2: OpenAxis and a selectable Rotation Mode

Start only after milestone 1 is complete. Keep its verified stock source,
toolchain, image identities and test results as an immutable reference for the
custom branch. Custom images are intentionally different and cannot inherit
the stock image's exact-match claim.

### 5. Obtain and pin the current OpenAxis specification

Use the [OpenAxis repository](https://github.com/rotatrix/openaxis), its
[authoritative wire specification](https://github.com/rotatrix/openaxis/blob/master/SPEC.md)
and [SDK installation guide](https://openaxis.rotatrix.com/guide/sdk-installation/).
At the start of this milestone, check for the latest published specification
and download a revision-pinned copy with matching SDK documentation and tests.
Record source URLs, release/version or commit, retrieval date, byte counts,
SHA-256s and licenses. Review applicable upstream terms before SDK reuse or
server implementation.
Check the supported versions and transport requirements of the intended
Rotatrix-compatible application extension. Do not rely on old notes or invent
protocol fields; resolve ambiguous or missing specifications before implementation.

The 2026-10-16 documentation check found OpenAxis 1.0 Release Candidate 1 at
commit `8f8b5e50e6eb1f3b15e2bd6ebaccc6208ce50bcc`. This is a research snapshot,
not a selection of the version to implement later. Retrieval identities are in
[openaxis-sources.json](openaxis-sources.json). Recheck when milestone 2 starts;
subsequent updates require an explicit compatibility review, not silent drift.

### 6. Implement compatible rotational data

The [checked specification](https://github.com/rotatrix/openaxis/blob/8f8b5e50e6eb1f3b15e2bd6ebaccc6208ce50bcc/SPEC.md)
defines a local WebSocket protocol using MessagePack between a host input
server and application clients. It explicitly excludes hardware reports and
device discovery. The [SDK guide](https://openaxis.rotatrix.com/guide/sdk-installation/)
also describes device verification; compatibility with a custom SlimBlade is
not established by the public client SDK.

Prefer device-side rotation processing, but do not assume that emitting USB
reports implements OpenAxis. A host component is the expected integration path
under the current specification (an architectural inference, not a tested
design). First establish whether Rotatrix supports ingesting the custom device's
input. If not, evaluate a small USB bridge/server against the required client
interface and applicable upstream terms before implementation. Native-only
support remains a preference to investigate, not a promised capability.

Test protocol conformance, units, direction, timing and error handling against
the pinned specification and the real extension. Preserve normal mouse
behavior outside Rotation Mode and check for regressions in retained modes.
Every modified firmware release needs independent review, the recovery gates
and a bounded hardware validation plan; the stock rebuild's success is not a
blanket flashing approval.

### 7. Add a button toggle

Choose the otherwise-unused physical button with the user before assigning it.
Make it toggle between normal Mouse Mode and Rotation Mode. Define the button's
event handling, debounce, mode indication and behavior across reconnects and
power cycles. Start in Mouse Mode by default unless the user chooses otherwise.
Switching modes must not leave held buttons, scrolling or rotation events stuck.
Test both transition directions and recovery to ordinary mouse use.

### Wireless preference and size limits

Preserve original Bluetooth and 2.4 GHz functionality where feasible. Measure
flash and RAM use before removing features; record the limiting budget and
tradeoffs. If size limits prevent OpenAxis integration, wireless is the first
optional functionality to remove in the custom branch. Never reclaim loader,
recovery, calibration or unknown storage to make room. Keep the exact stock
baseline intact regardless of later feature choices.

## Current position and next work

The [first six-task agent run](../decomp/results/pilot-run-20261016/notes.md) has
completed: all six drafts are reviewed, with independent exact-range rebuilds.
The [second run](../decomp/results/batch2-run-20261017/notes.md) is also complete:
four more reviewed drafts using the unchanged ARMCC5 profile. The
[broader workflow](broader-workflow.md) adds stock-qualified direct-call feedback,
guarded dispatch, frozen batch admission and explicit byte/dependency accounting.
[Batch 3 finished](../decomp/results/batch3-run-20261017/notes.md): fn_0000be60 is
reviewed and fn_000112b0 is terminal blocked. [Batch 4](batch-4.md) prepares three
new leaves with retained Rea evidence and unchanged compiler/verifier profiles.
Two earlier wrapper specimens serve as calibration, not worker assignments.
New runs require committed preparation, an explicit assignment and live quota.

The [isolated runner](swarm.md) retains bounded turns and the 45%-remaining
weekly stop chosen to preserve the user's 40% work reserve. No new quota window
or model run is assigned by preparation. All ten reviewed sources were freshly
rebuilt during broader preparation and still reproduce their complete owned ranges.

The runtime-helper call model and inline-data analysis were repaired on a
separate project copy, checked against 10,368 original-instruction executions,
and replayed. Zero saved analysis errors does not approve all discovered
boundaries. Local ARMCC5 runs headlessly under Wine with the supplied
Professional key; no additional compiler installer, Windows desktop or licence
request is needed for the demonstrated leaf profile. The exact historical
compiler remains unknown. Matching coverage is unknown.

Full-image linking, independent certification and the
[dependency/storage ledger](dependencies.md) remain milestone work. Bounded
direct-call qualification and guarded integration are implemented; shared data
and interworking still need further verifier support.
The full hardware gates still apply, and no current result establishes safe
flashing. See [the workflow](workflow.md).

This roadmap is not an instruction to run all stages immediately. Documentation
cleanup and offline tasks do not initiate device access, loader entry, HID/vendor
reports, flashing, purchases or paid agent jobs. Hardware actions need their
own explicit session request and the gates above. Existing bootstrap task
packets remain narrowly scoped; their no-decompilation rule applies to those
setup assignments, not to the project's reconstruction goal.
