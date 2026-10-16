// Correct two independently checked decode sites, never firmware bytes.
// Deliberately leave the inline-data/runtime-dispatch error unresolved.
// @category SlimBlade
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;

public class RepairConfirmedAnalysis extends GhidraScript {
    private static final String SHA = "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7";
    private String hex(long x) { return String.format("0x%08x", x); }
    private void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
    private byte[] container() throws Exception {
        byte[] result = new byte[128112];
        require(currentProgram.getMemory().getBytes(toAddr(0), result) == result.length, "short container read");
        return result;
    }
    private void word(long address, int expected) throws Exception {
        require(getInt(toAddr(address)) == expected, "word anchor changed at " + hex(address));
    }
    private JsonObject snapshot(long address) throws Exception {
        CodeUnit unit = currentProgram.getListing().getCodeUnitAt(toAddr(address));
        require(unit != null, "missing code unit at " + hex(address));
        JsonObject row = new JsonObject();
        row.addProperty("address", hex(address));
        row.addProperty("bytes", HexFormat.of().formatHex(unit.getBytes()));
        row.addProperty("text", unit.toString());
        row.addProperty("instruction", unit instanceof Instruction);
        row.addProperty("tmode", currentProgram.getProgramContext().getValue(
            currentProgram.getRegister("TMode"), toAddr(address), false));
        return row;
    }
    private void decode(long start, long end) throws Exception {
        Register mode = currentProgram.getRegister("TMode");
        // Only set the cleared seed; existing Thumb instructions later in the
        // range retain their own context. Ghidra rejects writes over code.
        currentProgram.getProgramContext().setValue(mode, toAddr(start), toAddr(start), BigInteger.ONE);
        var command = new DisassembleCommand(toAddr(start), new AddressSet(toAddr(start), toAddr(end)), true);
        command.enableCodeAnalysis(false);
        require(command.applyTo(currentProgram, monitor), "disassembly failed: " + command.getStatusMsg());
    }
    private void extend(long entry, long start, long end) throws Exception {
        Function function = getFunctionAt(toAddr(entry));
        require(function != null, "function missing at " + hex(entry));
        AddressSet body = new AddressSet(function.getBody());
        body.add(toAddr(start), toAddr(end));
        function.setBody(body);
    }
    @Override
    public void run() throws Exception {
        int transaction = currentProgram.startTransaction("Bounded readiness analysis repair");
        boolean success = false;
        try {
            repair();
            success = true;
        }
        finally {
            currentProgram.endTransaction(transaction, success);
        }
    }
    private void repair() throws Exception {
        require(state.getProject().getName().startsWith("SlimBlade-v449-readiness"),
            "run only on a separate SlimBlade-v449-readiness project");
        require(getScriptArgs().length == 1, "Usage: RepairConfirmedAnalysis.java NEW_AUDIT.json");
        Path output = Path.of(getScriptArgs()[0]);
        require(!Files.exists(output), "refusing to overwrite audit");
        byte[] before = container();
        require(SHA.equals(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(before))), "wrong baseline");
        require("ARM:LE:32:v5t".equals(currentProgram.getLanguageID().toString()), "wrong language");
        word(0x4000, 0x46682107);
        word(0xa1d4, 0x0000bdf0);
        require(Short.toUnsignedInt(getShort(toAddr(0x3fd2))) == 0xe015, "Thumb branch anchor changed");
        require(Short.toUnsignedInt(getShort(toAddr(0x3ffe))) == 0x7048, "Thumb fallthrough anchor changed");
        require(Short.toUnsignedInt(getShort(toAddr(0xa1d2))) == 0xb005, "epilogue anchor changed");
        Instruction wrong = getInstructionAt(toAddr(0x4000));
        require(wrong != null && wrong.getLength() == 4, "expected old ARM misdecode");
        require(getDataAt(toAddr(0xa1d4)) != null, "expected old pointer misclassification");
        JsonObject audit = new JsonObject();
        JsonArray resolved = new JsonArray();
        for (long address : new long[] {0x4000, 0x4004, 0xa1d4}) {
            Bookmark[] bookmarks = currentProgram.getBookmarkManager().getBookmarks(toAddr(address), BookmarkType.ERROR);
            require(bookmarks.length == 1 && "Bad Instruction".equals(bookmarks[0].getCategory()),
                "expected one original decode error at " + hex(address));
            JsonObject row = new JsonObject();
            row.addProperty("address", hex(address));
            row.addProperty("category", bookmarks[0].getCategory());
            row.addProperty("message", bookmarks[0].getComment());
            resolved.add(row);
        }
        JsonArray oldUnits = new JsonArray();
        oldUnits.add(snapshot(0x4000)); oldUnits.add(snapshot(0xa1d4));
        audit.add("before", oldUnits);

        currentProgram.getListing().clearCodeUnits(toAddr(0x4000), toAddr(0x4003), false);
        decode(0x4000, 0x4025);
        currentProgram.getListing().clearCodeUnits(toAddr(0xa1d4), toAddr(0xa1d7), false);
        decode(0xa1d4, 0xa1d5);
        JsonArray decoded = new JsonArray();
        for (long address = 0x4000; address < 0x4026;) {
            Instruction instruction = getInstructionAt(toAddr(address));
            require(instruction != null, "decode hole at " + hex(address));
            require(BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                currentProgram.getRegister("TMode"), toAddr(address), false)), "not Thumb");
            decoded.add(snapshot(address));
            address += instruction.getLength();
        }
        require(getInstructionAt(toAddr(0x4024)).getFlowType().isTerminal(), "missing first return");
        require(getInstructionAt(toAddr(0xa1d4)).getFlowType().isTerminal(), "missing second return");
        decoded.add(snapshot(0xa1d4));
        extend(0x3f48, 0x4000, 0x4025);
        extend(0xa14c, 0xa1d4, 0xa1d5);

        // Retire only the three now-resolved error bookmarks, after assertions.
        for (long address : new long[] {0x4000, 0x4004, 0xa1d4}) {
            Bookmark[] bookmarks = currentProgram.getBookmarkManager().getBookmarks(toAddr(address), BookmarkType.ERROR);
            for (Bookmark bookmark : bookmarks) {
                require("Bad Instruction".equals(bookmark.getCategory()), "unexpected error category");
                currentProgram.getBookmarkManager().removeBookmark(bookmark);
            }
        }
        require(Arrays.equals(before, container()), "firmware bytes changed");
        require(getInstructionAt(toAddr(0x1e47c)).getFallThrough().equals(toAddr(0x1e480)),
            "unresolved runtime call was unexpectedly overridden");
        require(currentProgram.getBookmarkManager().getBookmarks(toAddr(0x1e480), BookmarkType.ERROR).length > 0,
            "unresolved diagnostic must remain visible");
        audit.addProperty("container_sha256", SHA);
        audit.addProperty("firmware_bytes_changed", false);
        audit.add("after", decoded);
        audit.add("resolved_errors", resolved);
        audit.addProperty("unresolved", "0x1e480: inline data consumed by runtime dispatcher at 0x1e4f0; call/continuation and shared-tail model needs review");
        Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(audit) + "\n", StandardOpenOption.CREATE_NEW);
        println("Corrected two decode sites; three diagnostics resolved, runtime-dispatch diagnostic preserved.");
    }
}
