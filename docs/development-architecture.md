# Custom firmware architecture

Last checked: 2026-08-15

## Direction

Stock mouse behaviour is replaceable. The useful stock boundary is the proven
startup, persistent-marker path, wired USB enumeration, endpoint service, and
resident-loader command. Wireless operation is outside project scope.

| Layer | Initial policy | Long-term direction |
| --- | --- | --- |
| Startup and recovery | Protect and byte-audit | Keep a minimal verified boot boundary |
| Wired USB transport | Retain stock implementation | Extend reports; replace only if required |
| Sensors and buttons | Reverse engineer | Replace with typed Rust drivers |
| Movement and reports | Treat as replaceable | Implement raw rotation and desired behaviour |
| Wireless code | Not required | Reclaim only after proving it unreachable in wired mode |

The development invariant is:

`protected initialization -> committed recovery marker -> experimental code`

Stock USB command `0x0d` is the fast loader path while its dispatcher remains
alive. A USB power cycle is the independent fallback after the marker commits.
No experimental sensor, button, report, or USB code may access marker storage,
application flash, or the protected pre-marker control flow.

## Incremental transport plan

1. Use the existing 17-byte vendor reports for register reads, sensor snapshots,
   button states, and low-rate diagnostics.
2. Add a RAM ring buffer or reuse a stock interrupt-IN endpoint if polling is
   insufficient.
3. Extend HID/vendor descriptors and reports for continuous raw rotation.
4. Replace the low-level USB stack only if the stock transport cannot meet the
   required bandwidth or semantics.

Known anchors already include the vendor dispatcher at `0x18f50–0x18fee`, its
carrier call at `0x18fba`, stock loader entry near `0x1895d`, response handling
at `0x18f6e–0x18fd4`, USB interfaces `00` and `01`, and descriptors near
`0x1e7d1`. The complete USB call graph remains open.

## Current priority

The build-only `0459` candidate now targets a dormant hook after stock
initialization. It runs only after command `0x0e` has committed the marker and
armed reserved mode `3`; see
[`post-init-marker.md`](post-init-marker.md). Hardware proof remains required.
The next stage proves the marker writer in that hooked context. Only the final
stage removes the USB arming requirement and places the automatic marker at the
`0x19bee` boundary.

After that gate, map the protected wired-USB call graph and reclaim only code
whose wired-mode unreachability is demonstrated by static references and live
tests.
