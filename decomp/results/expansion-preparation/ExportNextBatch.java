// Read-only evidence export. No analysis, pseudocode, or firmware source generation.
// @category SlimBlade
import com.google.gson.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class ExportNextBatch extends GhidraScript {
    private void require(boolean ok, String message) {
        if (!ok) throw new IllegalStateException(message);
    }
    private String hex(long x) { return String.format("0x%08x", x); }
    public void run() throws Exception {
        require(getScriptArgs().length == 1, "supply fresh output JSON path");
        byte[] raw = new byte[128112];
        require(currentProgram.getMemory().getBytes(toAddr(0), raw) == raw.length, "short read");
        String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
        require(sha.equals("e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"), "baseline changed");
        require(currentProgram.getLanguageID().toString().equals("ARM:LE:32:v5t"), "wrong language");
        JsonObject result = new JsonObject();
        result.addProperty("baseline_sha256", sha);
        result.addProperty("language", currentProgram.getLanguageID().toString());
        JsonArray functions = new JsonArray();
        long[][] spans = {{0x13f58,0x13f72}, {0x13f72,0x13f7a},
                          {0x154d4,0x154ea}, {0x18100,0x18114},
                          {0x6464,0x646e}, {0x6500,0x650a}};
        for (long[] span : spans) {
            long start = span[0], end = span[1];
            Function f = getFunctionAt(toAddr(start));
            require(f != null && f.getBody().getNumAddressRanges() == 1 &&
                f.getBody().getMinAddress().equals(toAddr(start)) &&
                f.getBody().getMaxAddress().equals(toAddr(end-1)), "boundary mismatch");
            JsonObject fn = new JsonObject();
            fn.addProperty("entry", hex(start)); fn.addProperty("end_exclusive", hex(end));
            JsonArray instructions = new JsonArray();
            for (long a = start; a < end;) {
                Instruction i = getInstructionAt(toAddr(a));
                require(i != null && (i.getLength() == 2 || i.getLength() == 4)
                    && a + i.getLength() <= end, "unexpected decode");
                require(BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                    currentProgram.getRegister("TMode"), toAddr(a), false)), "not Thumb");
                require(currentProgram.getBookmarkManager().getBookmarks(toAddr(a), BookmarkType.ERROR).length == 0,
                    "analysis diagnostic in candidate");
                JsonObject row = new JsonObject();
                row.addProperty("address", hex(a)); row.addProperty("bytes", HexFormat.of().formatHex(i.getBytes()));
                row.addProperty("text", i.toString()); row.addProperty("tmode", 1);
                row.addProperty("flow_type", i.getFlowType().toString());
                row.addProperty("fallthrough", i.getFallThrough() == null ? null : hex(i.getFallThrough().getOffset()));
                JsonArray flows = new JsonArray();
                for (var target : i.getFlows()) flows.add(hex(target.getOffset()));
                row.add("flows", flows); instructions.add(row); a += i.getLength();
            }
            fn.add("instructions", instructions); functions.add(fn);
        }
        result.add("functions", functions);
        result.addProperty("scope", "four leaf proposals and two deferred direct-call wrappers; not launch approval");
        Files.writeString(Path.of(getScriptArgs()[0]), new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n",
            StandardOpenOption.CREATE_NEW);
    }
}
