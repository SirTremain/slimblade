# Recovery-stub scaffold

This is an offline ARM968E-S recovery-path reconstruction. **Do not flash its output without a separate explicit decision.** It installs an ARM vector table, switches to supervisor mode, sets a stack, writes the stock v4.49 loader-entry marker through the reconstructed BK3635 nonvolatile-memory controller, waits through the stock delay path, and requests a watchdog reset.

The register sequence is derived from exact stock application disassembly and
is checked by a hash-locked offline verifier. The same MMIO sequence passed on
hardware inside the stock recovery carrier. The standalone startup operations
normalize to the startup trampoline that subsequently ran successfully on the
BK3635. Three clean builds were byte-identical. The exact standalone image then
ran successfully, wrote the loader marker, reset, and returned as a new
`25a7:fabe` loader that answered BK3635 type `d2`. The generated file retains
its `DO_NOT_FLASH` name because another hardware write still requires a separate
explicit decision.

These C/assembly sources are retained as readable evidence for the proven
milestone. They are no longer an active build. The Rust verifier preserves its
exact code, container, call-graph, MMIO, and recovery invariants.
