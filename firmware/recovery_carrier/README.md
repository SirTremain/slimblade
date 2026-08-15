# Stock recovery carrier

This historical probe injected staged MMIO tests into an otherwise stock v4.49
application. Stock command `0x0d` remained available; `0x0e` probed a
non-writing storage read, `0x0f` probed watchdog reset, and `0x10` performed the
reconstructed marker/reset path.

The assembly and linker script remain as readable evidence. The Rust verifier
preserves the exact derivation, hash, branches, MMIO ordering, and image checks;
this directory is no longer an active build.
