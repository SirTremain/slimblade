# Stock startup trampoline

This `4.53` candidate derives from the live-proven `4.52` reset trampoline. It exercises the standalone stub's CPU-mode setup, stack load, and ARM-to-Thumb entry, then returns to ARM, restores the incoming state, and resumes stock startup. The proven carrier commands remain present.

The generated artifact is intentionally named `DO_NOT_FLASH-stock-startup-trampoline.container.bin`; building and auditing it does not access USB.
