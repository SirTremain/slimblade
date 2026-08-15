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

The `0459` preflight disproved the initially identified wired-loop state. The
corrected `0460` probe proved that command `0x0e` can commit the marker and set
the actual live state byte, but state `5` did not dispatch through the assumed
default switch route; see [`post-init-marker.md`](post-init-marker.md).

After confirming cold-power loader recovery, restore the audited working image
and trace the actual state-dispatch path. That trace identified the internal
wired loop at `0x1cfcc`; the separately hashed `0461` candidate now targets it
while retaining the same marker-first arming sequence. It must prove control
flow returns to stock state before any automatic marker placement is attempted.

Live testing showed `0x1cfcc` is not revisited after USB becomes active. The
`0462` candidate wraps the deeper steady-state service call at `0x1d3c2`, calls
its original stock target first, and retains the same marker-first arm. Its
unarmed flash booted with normal input, but the explicit `0x0e` arm remained at
state `5`; this boundary is also not traversed after the USB command. The
marker-first cold-power fallback passed and audited `0453` was restored.
Automatic marker placement remains gated on finding and live-proving a
recurrently traversed boundary.

Static tracing then found a stronger synchronous boundary: caller `0x1c55a`
invokes the proven live vendor dispatcher at `0x18f4c`, which calls the custom
handler at `0x18fba` and returns only after completing the stock response path.
The separately hash-locked `0463` candidate wraps that call and checks the
armed state immediately after its return. This removes the unproven
outer-loop-recurrence assumption; an unarmed boot and explicit marker-first
arm were live-proven, normal input remained functional, and marker-driven
cold-power recovery returned the resident loader. Audited `0453` was then
restored. This establishes the dispatcher-return boundary as the safe entry
point for subsequent experimental code.

After that gate, map the protected wired-USB call graph and reclaim only code
whose wired-mode unreachability is demonstrated by static references and live
tests.
