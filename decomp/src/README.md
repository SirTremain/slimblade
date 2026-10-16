# Reconstructed source

Stock reconstruction for milestone 1 of the [project plan](../../docs/project-plan.md).
No function assignments exist yet. Initially use one C file per assigned
function (`fn_<eight-digit-even-address>.c`). Stable address IDs survive renames.
The coordinator may group completed functions into translation units once
original file boundaries and compiler behavior are understood.

Do not add stub functions, raw instruction arrays or inline assembly to claim
progress. Necessary hand-written startup/interrupt assembly must be tracked
separately and excluded from the recovered-C metric.
Preserve wireless and other stock behavior here. OpenAxis and button-toggle
changes start only after the verified stock milestone, in a separate custom branch.
