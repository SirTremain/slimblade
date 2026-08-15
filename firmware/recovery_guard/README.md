# Marker-first recovery guard

This is the first live-proven guard. It preserves the exact live-proven
recovery stub through loader-marker completion, then changes only its final call
to enter a two-byte deliberate Thumb hang at `0x21c4` instead of resetting.

After that hang, a physical power cycle should enter the resident loader because
the marker was already written. This tests the fallback invariant needed before
real experimental code is placed at the same entry. It does not access USB while
building and must not be flashed without a separate explicit decision.

The 2026-08-14 test and Rust-only 2026-08-15 cutoff both produced the intended
USB silence. A complete USB power cycle entered the resident loader, which
answered `B2/d2` and successfully restored the proven v4.53 image. See
[`../../docs/recovery-guard.md`](../../docs/recovery-guard.md).

The active Rust builder and conservative storage-isolation checks run through
`cargo xtask all`. Future experiments must keep these checks and must not link
persistent-storage drivers. Files in this directory are retained milestone
references; active firmware lives in [`../bk3635-rs`](../bk3635-rs).
