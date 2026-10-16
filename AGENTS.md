# Repository guidance

## Scope

The active project is offline reconstruction of stock SlimBlade Pro firmware.
Do not flash, reset, enter the loader, send HID/vendor reports, access a device,
or restore retired flashing tools as part of decompilation work. Earlier
standing approval for diagnostic flashes does not apply to this workflow.
Hardware work needs a new explicit user request. Preserve the historical
[marker reachability requirement](docs/marker-reachability-gate.md).

The eventual custom firmware needs wired USB only. During reconstruction,
account for all code and data in the chosen stock image, including wireless
paths, before claiming a complete rebuild. Firmware modifications come later.

## Agent work

- Read [the workflow](docs/workflow.md) and your assigned task packet.
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
