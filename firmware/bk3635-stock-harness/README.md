# Stock-hosted recovery harnesses

This isolated workspace builds two reviewed injections while retaining complete
Kensington startup, USB, and interrupt handlers:

- `slimblade-stock-harness`: the tested `0455` early-marker experiment;
- `slimblade-late-marker-probe`: the build-only `0456` compatibility probe,
  which writes the marker only from post-startup command `0x0e`.

The linked injection occupies only the verified `0x21ac–0x22ff` stock gap.
No build command accesses hardware. Exact artifact identities and the proposed
live sequence are recorded in `../../docs/stock-harness.md`.

Run `cargo xtask stock-harness` or `cargo xtask late-marker-probe` from the
repository root. Generated `DO_NOT_FLASH` artifacts remain under `target/`.
