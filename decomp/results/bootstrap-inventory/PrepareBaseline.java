// Establish conservative mappings and evidence-backed instruction-state seeds.
// No decompiler is invoked. Raw input bytes are never changed.
// @category SlimBlade
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.lang.Register;
import java.math.BigInteger;

public class PrepareBaseline extends GhidraScript {
    private void requireWord(long address, int expected) throws Exception {
        if (getInt(toAddr(address)) != expected) {
            throw new IllegalStateException("Anchor mismatch at " + toAddr(address));
        }
    }
    private void seed(long address, boolean thumb, String name) throws Exception {
        Register mode = currentProgram.getRegister("TMode");
        currentProgram.getProgramContext().setValue(mode, toAddr(address),
            toAddr(address), thumb ? BigInteger.ONE : BigInteger.ZERO);
        if (!disassemble(toAddr(address))) {
            throw new IllegalStateException("Disassembly seed failed: " + name);
        }
        createFunction(toAddr(address), name);
    }
    @Override
    public void run() throws Exception {
        if (!"ARM:LE:32:v5t".equals(currentProgram.getLanguageID().toString()) ||
            currentProgram.getRegister("TMode") == null) {
            throw new IllegalStateException("ARM:LE:32:v5t with TMode is required (v5 is ARM-only)");
        }
        if (!"e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"
            .equalsIgnoreCase(currentProgram.getExecutableSHA256())) {
            throw new IllegalStateException("Unexpected baseline");
        }
        requireWord(0x2020, 0xe59ff018);
        requireWord(0x2040, 0x2064);
        requireWord(0x2058, 0x2320);
        requireWord(0x205c, 0x2300);
        requireWord(0x2170, 0x19879);
        requireWord(0x2194, 0x1ed60);
        requireWord(0x2198, 0x400020);
        requireWord(0x219c, 0x6f4);
        requireWord(0x21a0, 0x3940);
        requireWord(0x21a4, 0x400714);
        Memory mem = currentProgram.getMemory();
        // Boundaries classify known storage; executable blocks still contain
        // undiscovered data. Unknown prefix is retained, not declared loader code.
        long[] boundaries = {0x2000, 0x2020, 0x1ed60, 0x1f454};
        for (long boundary : boundaries) {
            mem.split(mem.getBlock(toAddr(boundary)), toAddr(boundary));
        }
        String[] names = {"container_prefix_unknown", "application_metadata",
            "application_mixed_code_data", "ram_data_load_image", "trailer_unknown"};
        MemoryBlock[] blocks = mem.getBlocks();
        for (int i = 0; i < blocks.length; i++) {
            blocks[i].setName(names[i]);
            blocks[i].setRead(true);
            blocks[i].setWrite(false);
            blocks[i].setExecute(i == 2);
        }
        // A post-startup analysis copy, not proof RAM contains this data on reset.
        byte[] init = new byte[0x6f4];
        mem.getBytes(toAddr(0x1ed60), init);
        MemoryBlock data = mem.createInitializedBlock("ram_data_after_startup",
            toAddr(0x400020), new java.io.ByteArrayInputStream(init), init.length, monitor, false);
        data.setRead(true); data.setWrite(true); data.setExecute(false);
        MemoryBlock bss = mem.createUninitializedBlock("ram_bss", toAddr(0x400714), 0x3940, false);
        bss.setRead(true); bss.setWrite(true); bss.setExecute(false);
        // Only observed stack guard words are mapped. Gaps, full RAM capacity,
        // MMIO blocks and aliases await direct reference review.
        for (long guard : new long[] {0x4073b0, 0x4073bc, 0x407abc, 0x407dbc, 0x407efc}) {
            MemoryBlock block = mem.createUninitializedBlock("stack_anchor_" + Long.toHexString(guard),
                toAddr(guard), 4, false);
            block.setRead(true); block.setWrite(true); block.setExecute(false);
        }
        // Avoid pseudocode-based parameter inference during bootstrap inventory.
        setAnalysisOption(currentProgram, "Decompiler Parameter ID", "false");
        setAnalysisOption(currentProgram, "Decompiler Switch Analysis", "false");
        setAnalysisOption(currentProgram, "ARM Constant Reference Analyzer.Trust values read from writable memory", "false");
        seed(0x2060, false, "vector_exception_loop");
        seed(0x2064, false, "reset_anchor");
        seed(0x2300, false, "fiq_wrapper_anchor");
        seed(0x2320, false, "irq_wrapper_anchor");
        seed(0x19878, true, "application_entry_anchor");
        disassemble(toAddr(0x2020));
        println("Prepared mapping and ARM/Thumb anchors; discovery remains incomplete.");
    }
}
