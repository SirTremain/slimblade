# Repository guidance

## Purpose

This repository tracks investigation of the Kensington SlimBlade Pro, especially its dual sensors, stock USB reports, and firmware-update path.

The custom-firmware target only needs wired USB operation. Preserving Bluetooth, 2.4 GHz dongle support, pairing, battery operation, or other wireless behavior is not a project requirement.

## Working rules

- Keep notes concise and separate verified observations, inferences, and open questions.
- Record source URLs, retrieval dates, exact byte counts, and SHA-256 hashes for inspected artifacts.
- Do not commit Kensington firmware or updater binaries unless the user explicitly requests it. Use temporary storage for analysis.
- Prefer read-only inspection, extraction, and USB capture. The user has given standing approval for audited diagnostic iterations that preserve the proven marker guard and use the tested USB loader path; do not pause for each such flash. Stop for audit failures, a changed risk boundary, or required physical interaction. If an experiment fails and the marker guard returns the device to resident loader, restore the exact audited v4.53 startup-trampoline container without separate approval after verifying its locked SHA-256.
- Treat marker reachability as a release-blocking invariant for every custom firmware version. Presence or byte identity of the marker writer is insufficient: the verifier must prove the wired reset path reaches and completes it before any replaceable code, and the first hardware run must prove cold-power loader entry. Never flash a new custom version if either gate is absent or fails; see `docs/marker-reachability-gate.md`.
- Preserve unrelated repository changes and use relative links between documents.
- Do not describe user actions as permitted by the agent, and do not use first-person plural language to imply shared agency.
- If privileged work is necessary, explain one short command at a time and place each user-run command in its own fenced block.
