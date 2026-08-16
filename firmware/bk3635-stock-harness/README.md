# Stock-hosted recovery harnesses

This isolated workspace builds reviewed injections while retaining complete
Kensington startup, USB, and interrupt handlers:

- `slimblade-stock-harness`: the tested `0455` early-marker experiment;
- `slimblade-late-marker-probe`: the build-only `0456` compatibility probe,
  which writes the marker only from post-startup command `0x0e`;
- `slimblade-experiment-entry-probe`: the build-only `0457` probe, whose
  command `0x0e` writes the same marker and then deliberately hangs;
- `slimblade-rust-response-probe`: the build-only `0458` probe, which runs an
  eight-byte Rust function after the marker and returns signature `0x58`;
- `slimblade-post-init-hook-probe`: a build-only dormant main-loop hook. Command
  `0x0e` commits the marker before arming reserved mode `3`; command `0x0f`
  reports whether the hook restored stock wired mode `2`.
- `slimblade-dispatcher-return-hook-probe`: the `0463` marker-first candidate,
  which wraps the proven live stock vendor-dispatch call and consumes armed
  state `5` only after that call returns.
- `slimblade-experiment-dispatch-guard`: the live-tested `0464` reusable entry,
  which clears armed state `5` before calling a returning Rust experiment and
  keeps the nested call boundaries 8-byte stack aligned.
- `slimblade-input-diagnostics`: the live-tested `0465` read-only snapshot;
  its chosen stock report buffer remained zero during wired input.
- `slimblade-paged-input-diagnostics`: the build-only `0466` selector-based
  snapshot of proven button, combined-motion, and per-sensor RAM windows.
- `slimblade-sensor-shadow-diagnostics`: the live-tested `0470` pre-clear
  per-sensor shadow with a modulo-256 sequence for duplicate-free host reads.
- `slimblade-unsolicited-report-probe`: the build-tested `0471` marker-first
  one-shot re-arm of the stock endpoint-2 response path.
- `slimblade-custom-main-handoff-probe`: the build-tested `0472` automatic
  post-init marker followed by a deliberate non-returning custom-main stand-in.
- `slimblade-custom-main-usb-recovery-probe`: the build-tested `0473` automatic
  marker followed by a minimal custom loop that services stock USB recovery.
- `slimblade-custom-main-stream-transport-probe`: the build-tested `0474`
  stock wired initializer followed by a 148-byte Rust endpoint-2 transport
  loop that prioritizes recovery responses.
- `slimblade-custom-main-sensor-stream-probe`: the audited `0475` candidate
  calls the proven stock sensor service, accumulates both pre-clear sensor
  pairs, and retains endpoint-2 USB recovery.

Recovery code occupies the verified `0x21ac–0x22ff` stock gap. The `0474`
runtime additionally replaces `0x1c460..0x1c4f4` after the marker commits.
The `0475` runtime ends at `0x1c588`, preserving the wired initializer's
literal table at `0x1c58c..0x1c5bf`; its small hook and report encoder replace
only the entry of an unused wireless-mode routine at `0x1c5c0`.
No build command accesses hardware. Exact artifact identities and the proposed
live sequence are recorded in `../../docs/stock-harness.md`.

Run the corresponding `cargo xtask` command from the repository root. Generated
`DO_NOT_FLASH` artifacts remain under `target/`.
