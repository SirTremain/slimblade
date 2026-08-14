# Stock reset trampoline

This exact-hash `4.52` candidate derives from the proven `4.51` recovery carrier. It replaces the first stock reset-handler instruction with an ARM branch to two injected instructions at `0x22b4`: replay stock `mov r0, #0`, then return to stock at `0x2068`.

The mouse and all four carrier recovery commands otherwise remain intact. The artifact is intentionally named `DO_NOT_FLASH-stock-reset-trampoline.container.bin`; building and auditing it does not access USB.
