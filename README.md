# SlimBlade Pro research

Compact notes on the Kensington SlimBlade Pro sensor and firmware interface.

- [Firmware research](docs/firmware-research.md)
- [Custom-firmware and recovery gates](docs/custom-firmware-feasibility.md)
- [Recovery-stub path](docs/recovery-stub.md)
- [Stock recovery carrier](docs/recovery-carrier.md)
- [Reset trampoline](docs/reset-trampoline.md)
- [Development tooling](docs/development-tooling.md)
- [Board observations](docs/board-observations.md)

Linux development support:

- [`tools/slimblade_usb.py`](tools/slimblade_usb.py): guarded HID inspection, loader control, exact-hash images, and staged recovery-carrier commands.
- [`tools/firmware_image.py`](tools/firmware_image.py): offline BK3635 header/CRC inspection, application packaging, and stock-derived acceptance-probe generation.
- [`tools/verify_recovery_stub.py`](tools/verify_recovery_stub.py): hash-locked, offline stock/stub comparison and pre-flight checks.
- [`tools/verify_recovery_carrier.py`](tools/verify_recovery_carrier.py): verifies the safer stock-hosted staged MMIO probes.
- [`tools/verify_reset_trampoline.py`](tools/verify_reset_trampoline.py): verifies the two-instruction stock reset hook and exact return target.
- [`udev/70-slimblade-research.rules`](udev/70-slimblade-research.rules): permissions limited to the normal and known bootloader USB IDs.
