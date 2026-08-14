# Recovery-stub scaffold

This is an offline ARM968E-S recovery-path reconstruction. **Do not flash its output without a separate explicit decision.** It installs an ARM vector table, switches to supervisor mode, sets a stack, writes the stock v4.49 loader-entry marker through the reconstructed BK3635 nonvolatile-memory controller, waits through the stock delay path, and requests a watchdog reset.

The register sequence is derived from exact stock application disassembly and is checked by a hash-locked offline verifier. It has not run on hardware. The generated file is therefore intentionally named `DO_NOT_FLASH-recovery-stub.container.bin`.

Build with `make`. Run `make preflight` while the exact official v4.49 extraction is present at `/tmp/slimblade-v449.bin`. Generated files remain under ignored `build/`.
