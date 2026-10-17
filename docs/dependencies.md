# Stock reconstruction and dependency ledger

Updated 2026-10-17. Analysis baseline: v4.49, 128,112 bytes, SHA-256
`e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7`.
Sources and retrieval identity: [stock baseline](stock-baseline.md),
[acquisition record](../decomp/results/bootstrap-inventory/acquisition-record.json),
and [bootstrap evidence](../decomp/results/bootstrap-inventory/notes.md).
These ranges account for the container, not all physical device storage.

| Container range (end exclusive) | Bytes | Current treatment |
| --- | ---: | --- |
| `0x00000–0x02000` | 8,192 | Prefix; purpose/loader relationship unresolved, not recovered |
| `0x02000–0x02020` | 32 | Application metadata; packaging/checksums unresolved |
| `0x02020–0x1ed60` | 118,080 | Mixed ARM/Thumb code, pools/tables/padding; ten reviewed leaves own 174 bytes; two call tasks own 20 more bytes but have no recovered source; all other ownership unapproved |
| `0x1ed60–0x1f454` | 1,780 | Startup data-load image; source/types/relocations unresolved |
| `0x1f454–0x1f470` | 28 | Trailer; purpose/checksums unresolved |

All 128,112 bytes remain in the reconstruction denominator. The pilot neither
copies unknown regions into a supposed source build nor drops them from scope.
Decoded instruction counts, function-body unions and unclassified counts are
different discovery metrics, not recovered coverage.

Observed startup copies 1,780 bytes to RAM `0x400020–0x400714` and clears
`0x400714–0x404054`. This does not establish all RAM, aliases, stacks or physical
flash mappings. The fixed-address leaf comparison uses the verified flat
analysis model; it does not implement updater transport or flash mapping.

| Dependency/question | State and gate |
| --- | --- |
| Original compiler, ABI, linker, libraries | Historical provenance unknown; possible mixed components. ARMCC 5.06u7 b960 + strict LLD leaf layout reproduces all six calibration ranges. The new pinned feedback path is not a full-image toolchain or proof of original declarations. |
| Runtime dispatcher/callers | Analysis-only callfixup and corrected ownership validated and replayed; 10,368 original-byte cases agree. Nonstandard saved-frame exits remain explicit. See [preparation evidence](../decomp/results/preparation/notes.md); not recovered C. |
| Resident loader, ROM services, external firmware/storage | Existence, identity and extent unresolved. SDK boot files are leads, not this device's loader. |
| Updater framing, checksums and destination ranges | Historical evidence needs complete reproduction before hardware work. No updater is executed by the active tools. |
| Calibration, identity, pairing and nonvolatile device state | Location/readability/backup requirements unresolved; never regenerate from another device's dump. |
| Bluetooth and 2.4 GHz paths | Stock scope includes them all; no omission or custom feature removal during reconstruction. |
| Replacement device compatibility/recovery | Revision, installed firmware and application-independent recovery unestablished; hardware gate remains closed. |

The ten reviewed leaves have no observed outgoing calls, literal-pool/global
references or shared tails. Pointer arguments are supplied by callers, with
width/alignment/qualifier hypotheses documented in each packet. These local
facts support their narrow task boundaries. Compiler/build preparation now
passed for those completed batches. The [machine-readable ledger](../decomp/reconstruction.json)
now validates the full container denominator and records unresolved callee/RAM
dependencies. Batch-3 wrappers bind fixed callees but do not reconstruct them.
A separate user-assigned run/budget is still needed for new tasks. These
results do not establish safe flashing, complete dependency
coverage, an original toolchain or equivalence of a later modified image.
