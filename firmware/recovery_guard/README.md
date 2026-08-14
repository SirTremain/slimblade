# Marker-first recovery guard

This is the first live-proven guard. It preserves the exact live-proven
recovery stub through loader-marker completion, then changes only its final call
to enter a two-byte deliberate Thumb hang at `0x21c4` instead of resetting.

After that hang, a physical power cycle should enter the resident loader because
the marker was already written. This tests the fallback invariant needed before
real experimental code is placed at the same entry. It does not access USB while
building and must not be flashed without a separate explicit decision.

The 2026-08-14 hardware test produced the intended USB silence. A complete USB
power cycle with the battery disconnected then entered the resident loader,
which answered `B2/d2` and successfully restored the proven v4.53 image. See
[`../../docs/recovery-guard.md`](../../docs/recovery-guard.md).
