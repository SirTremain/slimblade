# Retired work

Current goals and hardware gates are defined in the [project plan](project-plan.md).
Old approvals, next-step lists, shopping recommendations and recovery commands
are historical context, not standing instructions for the replacement device.

The last pre-decompilation snapshot is commit
`ea2ee1dd6f47ab414180b1b4e6ea375caef489d7` (2026-10-16 cleanup baseline).
The user committed and pushed it before authorizing removal of tracked work.

The Rust workspaces, flashing CLI, custom firmware, SDK copy, migration files,
udev rules and superseded experiment notes were removed from the active tree.
Their source and recorded results remain in that commit. To inspect an old
file without restoring an executable workflow:

```sh
git show ea2ee1dd6f47ab414180b1b4e6ea375caef489d7:docs/firmware-research.md
```

Useful historical paths in that snapshot:

| Path | Evidence |
| --- | --- |
| `docs/firmware-research.md` | Official artifact identities, container and updater observations |
| `docs/bk3633-sdk-comparison.md` | Startup, USB and ARM/Thumb address anchors; SDK mismatches |
| `crates/slimblade-image/src/lib.rs` | Container and payload hash constants |
| `vendor/bk3633_sdk/UPSTREAM.md` | SDK origin and import provenance |
| `docs/custom-main-handoff.md` | Later experiments and their outcomes |

Retained as historical reference: [board observations](board-observations.md),
[hardware-loader research](hardware-loader-entry.md),
[bench notes](embedded-workbench.md), [pogo fixture](../hardware/pogo_fixture/README.md)
and [marker reachability](marker-reachability-gate.md). Old hardware results
concern the earlier device. The marker requirement remains a release gate for
modified firmware; the other documents are historical references, not active
decompilation or hardware assignments. The fixture work and local photographs
are preserved. Revalidate hardware and sources before promoting a historical
procedure into a new, explicitly scoped hardware session.

Ignored build products from the old workspace may still exist locally. They
are not active tools or evidence of a current build. The cleanup does not
uninstall host tools or system udev rules installed during earlier work.
