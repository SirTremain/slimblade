// Map only independently reviewed register addresses, not the related SDK map.
// @category SlimBlade
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.MemoryBlock;

public class MapObservedMMIO extends GhidraScript {
    private void block(long start, int size) throws Exception {
        MemoryBlock b = currentProgram.getMemory().createUninitializedBlock(
            "observed_mmio_" + Long.toHexString(start), toAddr(start), size, false);
        b.setRead(true); b.setWrite(true); b.setExecute(false); b.setVolatile(true);
    }
    @Override
    public void run() throws Exception {
        if (getInt(toAddr(0x179b4)) != 0x806000 ||
            getInt(toAddr(0x18018)) != 0x806500 ||
            getInt(toAddr(0x18024)) != 0x804000 ||
            getInt(toAddr(0x18028)) != 0x800040) {
            throw new IllegalStateException("MMIO literal anchor changed");
        }
        // 17998..1799c; 17f7a..17f8c; 17fec..17ffc; 1799e..179aa;
        // 17f5e..17f78. Access widths preserved by the instruction listing.
        block(0x80001c, 8);
        block(0x800040, 8);
        block(0x806000, 4);
        block(0x806520, 8);
        // Byte accesses in 17f8e..1800a only. No claim about intervening bytes.
        block(0x804000, 2);
        for (long offset : new long[] {0xb, 0xf, 0x80, 0x84, 0x88, 0x8c, 0x94, 0x9c}) {
            block(0x804000 + offset, 1);
        }
        setAnalysisOption(currentProgram, "ARM Constant Reference Analyzer.Trust values read from writable memory", "false");
        for (long vector = 0x2020; vector < 0x2040; vector += 4) disassemble(toAddr(vector));
        println("Mapped directly observed MMIO as volatile; unmapped addresses remain unresolved.");
    }
}
