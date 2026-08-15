# Stock-hosted recovery harnesses

This isolated workspace builds four reviewed injections while retaining complete
Kensington startup, USB, and interrupt handlers:

- `slimblade-stock-harness`: the tested `0455` early-marker experiment;
- `slimblade-late-marker-probe`: the build-only `0456` compatibility probe,
  which writes the marker only from post-startup command `0x0e`;
- `slimblade-experiment-entry-probe`: the build-only `0457` probe, whose
  command `0x0e` writes the same marker and then deliberately hangs;
- `slimblade-rust-response-probe`: the build-only `0458` probe, which runs an
  eight-byte Rust function after the marker and returns signature `0x58`.

The linked injection occupies only the verified `0x21ac–0x22ff` stock gap.
No build command accesses hardware. Exact artifact identities and the proposed
live sequence are recorded in `../../docs/stock-harness.md`.

Run the corresponding `cargo xtask stock-harness`, `late-marker-probe`, or
`experiment-entry-probe`, or `rust-response-probe` command from the repository
root. Generated `DO_NOT_FLASH` artifacts remain under `target/`.
