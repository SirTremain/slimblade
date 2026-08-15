# Repository guidance

## Purpose

This repository tracks investigation of the Kensington SlimBlade Pro, especially its dual sensors, stock USB reports, and firmware-update path.

The custom-firmware target only needs wired USB operation. Preserving Bluetooth, 2.4 GHz dongle support, pairing, battery operation, or other wireless behavior is not a project requirement.

## Working rules

- Keep notes concise and separate verified observations, inferences, and open questions.
- Record source URLs, retrieval dates, exact byte counts, and SHA-256 hashes for inspected artifacts.
- Do not commit Kensington firmware or updater binaries unless the user explicitly requests it. Use temporary storage for analysis.
- Prefer read-only inspection, extraction, and USB capture. Do not flash a device or modify hardware without an explicit request. Standing exception: after an explicitly requested experimental flash fails and the marker guard returns the device to resident loader, restore the exact audited v4.53 startup-trampoline container without requesting separate approval; verify its locked SHA-256 first.
- Preserve unrelated repository changes and use relative links between documents.
- Do not describe user actions as permitted by the agent, and do not use first-person plural language to imply shared agency.
- If privileged work is necessary, explain one short command at a time and place each user-run command in its own fenced block.
