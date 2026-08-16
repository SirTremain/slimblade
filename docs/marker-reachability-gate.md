# Marker reachability gate

Last checked: 2026-08-16

## Release-blocking task

Implement and require this gate for **every** custom firmware version. A build
must not be flashable merely because it contains the proven marker writer.

Before flashing, the verifier must:

1. Prove the wired reset path reaches `marker_set` and waits for successful
   storage completion before any experimental or reclaimable code can run.
2. Protect the complete transitive pre-marker control-flow closure, including
   mode-transition handlers and callees—not only the handoff and marker bytes.
3. Reject changed branches, indirect-dispatch inputs, or reclaimed regions that
   could prevent the marker handoff from being reached.

On the first hardware run of each version, complete USB power removal with the
battery disconnected must enumerate the resident loader. This cold-power test
is the final proof that the version actually committed the marker. Failure
retires the artifact immediately and blocks further flashing.

`0475` demonstrated why this is mandatory: it retained an identical marker
writer but replaced pre-marker handler `0x1c5c0`, making the writer unreachable.
