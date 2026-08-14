# Stock recovery carrier

This probe injects staged MMIO tests into an otherwise stock v4.49 application. Its output is not a general-purpose firmware image: only the exact audited hash is accepted by `tools/slimblade_usb.py`, after a separate explicit live-flash decision. Stock command `0x0d` remains available; `0x0e` probes a non-writing storage read, `0x0f` probes watchdog reset, and `0x10` performs the reconstructed marker/reset path.

The output is deliberately named `DO_NOT_FLASH-stock-recovery-carrier.container.bin`. Build artifacts remain under ignored `build/`.
