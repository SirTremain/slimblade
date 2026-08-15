# Marker-first stock harness

This build-only harness sets the live-proven recovery marker before resuming
complete Kensington startup. It retains the stock USB stack and recovery
command while providing power-cycle recovery if later custom code hangs.

The linked injection occupies only the verified `0x21ac–0x22ff` stock gap.
No build command accesses hardware. Exact artifact identities and the proposed
live sequence are recorded in `../../docs/stock-harness.md`.

Build and run every host-side audit with `cargo xtask stock-harness` from the
repository root. Generated `DO_NOT_FLASH` artifacts remain under `target/`.
