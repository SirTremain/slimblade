// Read-only, narrowly scoped evidence. No pseudocode or firmware C generation.
// @category SlimBlade
import com.google.gson.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class ExportPilot extends GhidraScript {
    private void require(boolean ok, String message) {
        if (!ok) throw new IllegalStateException(message);
    }
    private String hex(long x) { return String.format("0x%08x", x); }
    public void run() throws Exception {
        require(getScriptArgs().length == 1, "supply fresh output JSON path");
        byte[] container = new byte[128112];
        require(currentProgram.getMemory().getBytes(toAddr(0), container) == container.length, "short read");
        String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(container));
        require(sha.equals("e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"), "baseline changed");
        JsonObject result = new JsonObject();
        result.addProperty("baseline_sha256", sha);
        result.addProperty("language", currentProgram.getLanguageID().toString());
        JsonArray functions = new JsonArray();
        long[][] spans = {{0x3b48,0x3b64}, {0x3bb4,0x3bbe}, {0xe4ee,0xe4fc},
                          {0xe4fc,0xe512}, {0xe540,0xe548}, {0xe548,0xe558}};
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
                require(i != null && i.getLength() == 2, "unexpected decode");
                require(BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                    currentProgram.getRegister("TMode"), toAddr(a), false)), "not Thumb");
                require(!i.getFlowType().isCall(), "not leaf");
                require(currentProgram.getBookmarkManager().getBookmarks(toAddr(a), BookmarkType.ERROR).length == 0,
                    "analysis diagnostic in pilot");
                for (var target : i.getFlows())
                    require(target.getOffset() >= start && target.getOffset() < end, "escaping control flow");
                JsonObject row = new JsonObject();
                row.addProperty("address", hex(a)); row.addProperty("bytes", HexFormat.of().formatHex(i.getBytes()));
                row.addProperty("text", i.toString()); row.addProperty("tmode", 1);
                row.addProperty("flow_type", i.getFlowType().toString());
                row.addProperty("fallthrough", i.getFallThrough() == null ? null : hex(i.getFallThrough().getOffset()));
                JsonArray flows = new JsonArray();
                for (var target : i.getFlows()) flows.add(hex(target.getOffset()));
                row.add("flows", flows); instructions.add(row); a += i.getLength();
            }
            require(getInstructionAt(toAddr(end-2)).toString().equals("bx lr"), "missing return");
            fn.add("instructions", instructions); functions.add(fn);
        }
        result.add("functions", functions);
        result.addProperty("scope", "six locally reviewed leaves only; global inventory remains unapproved");
        Files.writeString(Path.of(getScriptArgs()[0]), new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n",
            StandardOpenOption.CREATE_NEW);
    }
}
