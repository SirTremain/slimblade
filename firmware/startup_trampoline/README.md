# Stock startup trampoline

This `4.53` candidate derives from the live-proven `4.52` reset trampoline. It exercises the standalone stub's CPU-mode setup, stack load, and ARM-to-Thumb entry, then returns to ARM, restores the incoming state, and resumes stock startup. The proven carrier commands remain present.

The exact audited artifact ran successfully on the BK3635 and returned as the
normal `047d:80d7` application with `bcdDevice 0453`. The generated file retains
the `DO_NOT_FLASH` name because another hardware write still requires a separate
explicit decision.

The assembly and linker script are retained milestone references. The Rust
builder/verifier preserves the exact 60 code bytes and container identity;
this directory is no longer an active build.
