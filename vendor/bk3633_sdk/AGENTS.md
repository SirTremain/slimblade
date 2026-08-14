# Vendored SDK guidance

- Preserve `LICENSE`, upstream copyright notices, and the provenance in
  `UPSTREAM.md`.
- Add a prominent BK3635 modification notice to every inherited source file
  that is changed.
- Prefer new BK3635-specific files and project directories when practical.
- Do not add generated binaries, maps, IDE state, PDFs, spreadsheets, or
  Kensington artifacts.
- Treat BK3633 peripheral definitions as unverified until matched against the
  SlimBlade firmware's instructions and MMIO behavior.
