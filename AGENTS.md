# Repository guidance

## Scope

Follow the [current project plan](docs/project-plan.md). Milestone 1 is complete
stock firmware reconstruction, any necessary dependency analysis, independent
exact-image verification, then gated flashing and hardware validation. Only
after that milestone passes does milestone 2 add the latest pinned OpenAxis
protocol and a user-selected button toggle between Mouse and Rotation modes.

Current work is offline. Do not flash, reset, enter the loader, send HID/vendor
reports, access a device or restore retired flashing tools during documentation
or decompilation tasks. The planned hardware milestone is not standing approval
to act on a device. A hardware session needs an explicit user request and the
plan's compatibility, backup, recovery and verification gates. Earlier approval
for diagnostic flashes does not carry over. Preserve the
[marker reachability requirement](docs/marker-reachability-gate.md) for modified
firmware; do not insert custom markers into a byte-identical stock rebuild.

Reconstruct all code and data in the selected stock image, including wireless
paths. Preserve Bluetooth and 2.4 GHz in the later custom firmware if feasible;
wireless is the first optional functionality to remove only if measured size
limits require it. Do not remove features during stock reconstruction. Prefer
device-side rotation processing, but distinguish USB device reports from the
host-facing OpenAxis protocol. A small host bridge is acceptable; verify the
supported ingestion path and SDK/device compatibility before implementation.

## Agent work

- Read the project plan, [the workflow](docs/workflow.md) and your assigned task
  packet. Historical notes are evidence, not current operating instructions.
- Work only on the assigned task and allowed paths in an isolated worktree.
  A coordinator owns the queue, shared headers, Ghidra database, toolchain,
  baseline, verifier and integration. Workers propose shared changes in notes.
- Ghidra pseudocode, names, comments, old notes and agent summaries are leads.
  Support conclusions with addresses, bytes, references and reproducible checks.
- Never change expected bytes, comparison rules, compiler flags or function
  boundaries merely to improve a score. Do not disguise original code bytes,
  inline assembly, post-link patches, stubs or omitted behavior as recovered C.
- Submitted/reviewed drafts are not matched functions. Only an independent,
  pinned compiler/linker/verifier pipeline may certify matches. That pipeline
  is not implemented yet; report matching coverage as unknown.
- Separate observed facts, inferences and unresolved questions. Preserve widths,
  signedness, aliasing, volatile MMIO, calling convention, ARM/Thumb state,
  side effects and original bugs. Do not redesign the firmware.
- Keep function attempts bounded: default 20 minutes, at most 8 compile/diff
  iterations, stop after 3 without improvement. Record blockers and hand off.
- Do not start paid/model jobs without a user-assigned run and budget. Do not
  commit or push unless the task requests it.

## Evidence and files

- Record artifact source URL, retrieval date, byte count and SHA-256.
- Keep Kensington binaries, updater packages, Ghidra projects, generated
  listings and evidence packets in temporary or ignored local storage. Do not
  commit or publish them unless explicitly requested.
- The replacement device's installed firmware and hardware revision have not
  been established. Historical v4.49 addresses are not proof about that device.
- Preserve unrelated edits and use relative links between repository documents.
- Use `apply_patch` for file edits. Use Python's standard library for scaffold
  tooling; run the offline tests after coordination changes.

## Communication

- Do not describe user actions as permitted or authorized by the agent.
- Do not use first-person plural language to imply shared agency or ownership.
- Perform non-privileged work directly. If privileged work is necessary,
  explain one short, inspectable command at a time; never hide it in a script.
- Put every user-run command in its own fenced block. Keep a naturally
  single-line command on one physical line.
