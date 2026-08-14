# Vendored BK3633 SDK

This source tree is the starting point for a wired-only BK3635 platform port.
See [`UPSTREAM.md`](UPSTREAM.md) for the exact source revision and import
filter, and [`../../docs/bk3633-sdk-comparison.md`](../../docs/bk3633-sdk-comparison.md)
for verified similarities and incompatibilities.

Do not assume that a BK3633 register definition applies to BK3635. Each reused
startup or peripheral operation needs stock-disassembly evidence and an
appropriate exact-byte, control-flow, or MMIO-side-effect comparison.

Generated build products and proprietary Kensington firmware do not belong in
this directory.
