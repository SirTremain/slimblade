# Rea integration: coordinator analysis

The first integration stage is operational: the coordinator can obtain Rea
function dossiers from a disposable copy of the corrected SlimBlade Ghidra
project. This is an optional analysis aid alongside the existing reconstruction
pipeline, not a replacement compiler, verifier or worker runner.

## What is integrated

- The unmodified Java bridge from the pinned `rea-agents` **6.5.0** npm archive.
  Only its two bridge sources and MIT licence are extracted. No npm lifecycle
  scripts, JavaScript dependencies, global setup or client registration run.
- [rea_bridge.py](../tools/rea_bridge.py), a Python-standard-library coordinator
  adapter with a small read-only RPC allowlist, serial execution and retained
  observations. It requests instructions, a function dossier and outgoing
  references for one to eight explicit function entries.
- [CheckReaProject.java](../ghidra/CheckReaProject.java), which checks mapped
  firmware bytes, saved function ranges/names/modes, the runtime call-fixup and
  inline-data repairs before and after queries.
- A summary/facet viewer that reads retained JSON and verifies its observation
  hash instead of repeating analysis. Upstream warnings and partial relationship
  coverage remain visible.

The complete archive URL, retrieval date, byte count, SHA-256 and npm integrity,
plus local project/Ghidra/JDK pins, are in [config.json](../decomp/rea/config.json).
Runs also retain their configuration and adapter source hash. The upstream MIT
licence is installed at `.decomp/rea/bridge-6.5.0/LICENSE`. Downloaded sources,
firmware-derived outputs, logs and project copies stay ignored under `.decomp/`.

This is a **custom saved-project adapter**, not an upstream-supported saved-project
provider or a fully registered Rea MCP server. Its JSON records are local bridge
observations, not Rea's canonical Evidence records. Do not feed them to upstream
evidence/verification APIs as though they were canonical bundles.

## Why not the default raw import?

The [reviewed upstream raw-binary route](https://github.com/morluto/rea/blob/8451d283920e86936576fdf67615807d1b4ca4a9/docs/raw-binary.md)
does not preserve this project's corrected mixed ARM/Thumb analysis and runtime
model. Its generic ARM profile selects `ARM:LE:32:v7`; this project's saved
language is `ARM:LE:32:v5t`. A fresh generic import would lose important repairs.
The [upstream Ghidra provider](https://github.com/morluto/rea/blob/8451d283920e86936576fdf67615807d1b4ca4a9/docs/ghidra-provider.md)
is designed around its own ephemeral import workflow.

The adapter instead copies the hash-pinned `SlimBlade-v449-runtime-v4` project,
opens only that copy with `-readOnly -noanalysis`, validates it, and runs the
unmodified bridge. After admission it sets Rea's raw-preparation readiness bit
only in the disposable program. That bit does **not** mean the upstream raw
preparation script ran. Ghidra discards those in-memory changes on close.

The GitHub documentation revision and npm package version are separate source
identities; no claim is made that their complete trees are identical.

## Running it

The tested local environment is Linux, bubblewrap 0.13.1, Ghidra 12.1.4 and the
existing pinned JDK 21.0.12.1+1. The config binds the current local project snapshot
and its owner; it is not an automatic portable project-bootstrap recipe. Missing
or changed prerequisites stop the adapter. Do not repin merely to bypass failure.
The zero-byte `.gpr` marker is normal; the `.rep` tree holds the database and is
separately content-pinned. Keep the original project closed while copying it.

Extract the already-downloaded, verified bridge (idempotent):

```sh
python3 tools/rea_bridge.py install
```

On a checkout missing the archive, explicitly download that exact pinned package:

```sh
python3 tools/rea_bridge.py install --fetch
```

Check local identities without starting Ghidra:

```sh
python3 tools/rea_bridge.py check
```

Create a new observation directory; choose a fresh name on subsequent runs:

```sh
python3 tools/rea_bridge.py analyze --entry 0xbe60 --entry 0x112b0 --output .decomp/rea/runs/wrapper-review-01
```

Read a compact retained summary:

```sh
python3 tools/rea_bridge.py inspect --run .decomp/rea/runs/wrapper-review-01 --entry 0xbe60
```

Read the relevant detail without starting Ghidra again:

```sh
python3 tools/rea_bridge.py inspect --run .decomp/rea/runs/wrapper-review-01 --entry 0xbe60 --facet assembly
```

Other facets include pseudocode, callers, callees, incoming/outgoing references,
basic blocks, native value flow and unresolved calls. Full responses remain in
the run directory. `report.json` must say `observed` and the original project
must remain unchanged; partial files from failed runs are diagnostic material.
Existing output directories are never overwritten. The default child deadline
is 300 seconds, configurable from 1 to 600; replies are capped at 8 MiB and a
watchdog terminates excessive logging or an overdue child. These are analysis
limits, separate from the existing worker attempt/time budget.

## Coordinator and worker use

The relevant practices from the
[upstream investigation guide](https://github.com/morluto/rea/blob/8451d283920e86936576fdf67615807d1b4ca4a9/.agents/skills/reverse-engineer-anything/SKILL.md)
are adapted here, not installed as a global skill or permission policy:

1. State a narrow question, exact target identity and candidate addresses.
2. Reuse retained observations from the same analysis profile. Read a summary
   before selecting detailed sections; expand only to answer a concrete gap.
3. Follow the relevant calls, data and state changes. Record observations,
   interpretations, contradictory evidence and unanswered questions separately.
4. Require the evidence appropriate to the claim: assembly/ABI review and pinned
   rebuilds for reconstructed C, not just plausible pseudocode.
5. Give independent assignments separate scopes and a shared evidence reference
   only during a user-assigned run through the existing bounded runner.

For a new batch, the coordinator may use these outputs while reviewing boundaries
and callee contracts. Copy relevant observations **with their limitations and
provenance** into a new immutable evidence packet before freezing its hash. Include
original bytes/listings from the existing exporter: Rea instruction text alone is
not a byte oracle. Do not edit old packets, reopen terminal tasks, expand verifier
support or change expected bytes merely because a dossier suggests something.

Workers still receive only their assigned packet. They do not receive this bridge,
its socket, the Ghidra project or compiler credentials. Follow
[broader intake](broader-workflow.md) and [swarm controls](swarm.md): explicit run
and budget, live quota, 45%-remaining stop, pause/new-window consent, at most two
bounded workers, serial pinned builds and independent unchanged-source review.
Integration does not launch workers or renew any previous assignment.

## Safety and interpretation

Bubblewrap isolates networking, processes and devices. The child receives only
system executables, pinned Ghidra/JDK/bridge/checker files and the disposable work
directory. It receives neither the original project, repository, real home,
licence files, queue nor host device nodes. A synthetic hosts file resolves only
the sandbox hostname without host DNS configuration.

The upstream Unix bridge truthfully advertises `read_only: false` because it
also implements annotation operations. This adapter exposes no generic RPC CLI:
its allowlist sends only the three observation methods plus ping/shutdown. The
temporary authenticated socket is coordinator-only and removed after the child
stops. This is not a general hardened service for other local same-user clients.

Observed caveats from the compatibility test:

- `0xbe60` pseudocode shows a no-argument call even though independent ABI review
  establishes argument forwarding. Do not replace its reviewed signature.
- Call relationships can be explicitly partial; an empty caller list does not
  prove the function is unused.
- Runtime dossiers retain injection/jumptable warnings and inferred register
  values. Preserving the repaired model does not make pseudocode original C.
- Rea body range ends are inclusive; repository packet `end_exclusive` is not.
  Non-contiguous bodies must not be flattened into one code span.

All 776 saved inventory entries can be checked for preservation without being
approved reconstruction assignments. No whole-image build, certified match,
hardware compatibility, flashing safety or speedup is established here.

## Validation and next integration stage

The [integration report](../decomp/results/rea-integration/notes.md) records actual
positive and negative controls. Synthetic adapter tests run with the ordinary
offline suite. Repeat the real local Ghidra controls explicitly:

```sh
SLIMBLADE_REA_INTEGRATION=1 python3 -m unittest discover -s tests -p test_rea_bridge_integration.py -v
```

Those tests create fresh ignored reports and deliberately corrupt only temporary
admission expectations to verify rejection. They do not modify firmware or pins.

The next useful stage is a small evidence-assisted intake of new functions using
this adapter, followed by packet review and an explicitly assigned bounded run.
Full Rea MCP/canonical Evidence integration would require a supported saved-project
provider or a maintained provider adaptation; it is not silently enabled here.
Rea's reconstruction checks would remain supplementary to the independent exact
image and hardware gates in the [project plan](project-plan.md).
