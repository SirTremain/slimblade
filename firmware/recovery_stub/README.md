# Recovery-stub scaffold

This is an offline ARM968E-S recovery-path reconstruction. **Do not flash its output without a separate explicit decision.** It installs an ARM vector table, switches to supervisor mode, sets a stack, writes the stock v4.49 loader-entry marker through the reconstructed BK3635 nonvolatile-memory controller, waits through the stock delay path, and requests a watchdog reset.

The register sequence is derived from exact stock application disassembly and
is checked by a hash-locked offline verifier. The same MMIO sequence passed on
hardware inside the stock recovery carrier. The standalone startup operations
normalize to the startup trampoline that subsequently ran successfully on the
BK3635. Three clean builds were byte-identical. These pieces have not yet run
together as this standalone image, so the generated file remains intentionally named
`DO_NOT_FLASH-recovery-stub.container.bin` and still requires a separate
explicit flash decision.

Build with `make`. Run `make preflight` while the exact official v4.49 extraction is present at `/tmp/slimblade-v449.bin`. Generated files remain under ignored `build/`.
