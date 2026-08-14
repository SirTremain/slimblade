# SlimBlade Pro research

Compact notes on the Kensington SlimBlade Pro sensor and firmware interface.

- [Firmware research](docs/firmware-research.md)
- [Custom-firmware and recovery gates](docs/custom-firmware-feasibility.md)
- [Recovery-stub path](docs/recovery-stub.md)
- [Stock recovery carrier](docs/recovery-carrier.md)
- [Reset trampoline](docs/reset-trampoline.md)
- [Startup trampoline](docs/startup-trampoline.md)
- [BK3633 SDK comparison](docs/bk3633-sdk-comparison.md)
- [Vendored BK3633 SDK](vendor/bk3633_sdk/README.md)
- [Development tooling](docs/development-tooling.md)
- [Board observations](docs/board-observations.md)

Linux development support:

- [`tools/slimblade_usb.py`](tools/slimblade_usb.py): guarded HID inspection, loader control, exact-hash images, and staged recovery-carrier commands.
- [`tools/firmware_image.py`](tools/firmware_image.py): offline BK3635 header/CRC inspection, application packaging, and stock-derived acceptance-probe generation.
- [`tools/disassemble_stock.py`](tools/disassemble_stock.py): hash-locked ARM/Thumb disassembly of selected official v4.49 ranges.
- [`tools/verify_recovery_stub.py`](tools/verify_recovery_stub.py): hash-locked, offline stock/stub comparison and pre-flight checks.
- [`tools/verify_recovery_carrier.py`](tools/verify_recovery_carrier.py): verifies the safer stock-hosted staged MMIO probes.
- [`tools/verify_reset_trampoline.py`](tools/verify_reset_trampoline.py): verifies the two-instruction stock reset hook and exact return target.
- [`tools/verify_startup_trampoline.py`](tools/verify_startup_trampoline.py): verifies CPU-mode, stack, and ARM/Thumb transition probes.
- [`udev/70-slimblade-research.rules`](udev/70-slimblade-research.rules): scoped permissions plus stable vendor-interface and loader symlinks.
