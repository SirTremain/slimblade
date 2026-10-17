// Local adapter admission. Runs only on a disposable project copy, without analysis.
// This is not REA's generic raw-binary import preparation.
// @category SlimBlade
import com.google.gson.*;
import ghidra.app.script.GhidraScript;
import ghidra.framework.Application;
import ghidra.program.database.SpecExtension;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

public class CheckReaProject extends GhidraScript {
    private void require(boolean ok, String why) {
        if (!ok) throw new IllegalStateException(why);
    }
    private long number(JsonElement value) {
        return Long.parseUnsignedLong(value.getAsString().substring(2), 16);
    }
    public void run() throws Exception {
        require(getScriptArgs().length == 2 && currentProgram != null, "admission input/output required");
        require(state.getProject().getName().equals("SlimBlade-rea-copy"), "disposable project required");
        JsonObject input = JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
        require(Application.getApplicationVersion().equals("12.1.4"), "wrong Ghidra version");
        require(currentProgram.getLanguageID().toString().equals("ARM:LE:32:v5t"), "wrong ARM/Thumb language");
        require(currentProgram.getCompilerSpec().getCompilerSpecID().toString().equals("default"), "wrong analysis compiler spec");
        require(currentProgram.getExecutableFormat().equals("Raw Binary"), "unexpected original import format");
        byte[] bytes = new byte[input.get("baseline_bytes").getAsInt()];
        require(currentProgram.getMemory().getBytes(toAddr(0), bytes) == bytes.length, "incomplete mapped baseline");
        String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        require(sha.equals(input.get("baseline_sha256").getAsString()), "database bytes differ from baseline");
        require(sha.equals(currentProgram.getExecutableSHA256()), "stored input identity differs");
        JsonArray functions = input.getAsJsonObject("inventory").getAsJsonArray("functions");
        int count = 0;
        var all = currentProgram.getFunctionManager().getFunctions(true);
        while (all.hasNext()) if (!all.next().isExternal()) count++;
        require(count == functions.size(), "function inventory changed");
        var modeRegister = currentProgram.getRegister("TMode");
        require(modeRegister != null, "missing TMode register");
        for (JsonElement value : functions) {
            monitor.checkCancelled();
            JsonObject row = value.getAsJsonObject();
            var address = toAddr(number(row.get("entry")));
            Function function = getFunctionAt(address);
            require(function != null && function.getName().equals(row.get("ghidra_name").getAsString()) &&
                    function.isThunk() == row.get("thunk").getAsBoolean(), "function identity changed at " + address);
            BigInteger mode = currentProgram.getProgramContext().getValue(modeRegister, address, false);
            String observed = mode == null ? "unknown" : mode.equals(BigInteger.ZERO) ? "arm" : "thumb";
            require(observed.equals(row.get("mode").getAsString()), "instruction mode changed at " + address);
            AddressSet expected = new AddressSet();
            for (JsonElement part : row.getAsJsonArray("ranges")) {
                JsonObject span = part.getAsJsonObject();
                expected.add(toAddr(number(span.get("start"))), toAddr(number(span.get("end_exclusive"))-1));
            }
            require(function.getBody().hasSameAddresses(expected), "body changed at " + address);
        }
        require("slimblade_v449_runtime".equals(getFunctionAt(toAddr(0x1e4f0)).getCallFixup()), "runtime fixup missing");
        String xml = SpecExtension.getCompilerSpecExtension(currentProgram,
            SpecExtension.Type.CALL_FIXUP, "slimblade_v449_runtime");
        require(xml != null && xml.trim().equals(input.get("runtime_xml").getAsString().trim()), "runtime model changed");
        for (long address : new long[]{0x1e364, 0x1e480}) {
            require(getInstructionAt(toAddr(address)) == null && getDataAt(toAddr(address)) != null &&
                    getDataAt(toAddr(address)).getLength() == 4, "inline data was decoded as code");
        }
        for (long address : new long[]{0x1e360, 0x1e47c})
            require(getInstructionAt(toAddr(address)).getFallThrough() == null, "runtime false fallthrough restored");
        require(currentProgram.getBookmarkManager().getBookmarkCount(BookmarkType.ERROR) == 0, "saved analysis errors");
        // Upstream requires this readiness bit for all Raw Binary Programs.
        // It is set ONLY after the stronger saved-project checks above. It does
        // not claim that ReaGhidraPrepareRaw ran, and is never saved to the source.
        currentProgram.getOptions(Program.PROGRAM_INFO).setBoolean("REA raw binary prepared", true);
        JsonObject result = new JsonObject();
        result.addProperty("status", "admitted");
        result.addProperty("adapter", "saved-project-bridge-v1");
        result.addProperty("sha256", sha);
        result.addProperty("functions_checked", count);
        result.addProperty("language", "ARM:LE:32:v5t");
        result.addProperty("runtime_fixup_preserved", true);
        result.addProperty("inline_data_preserved", true);
        result.addProperty("inventory_is_globally_reviewed", false);
        Files.writeString(Path.of(getScriptArgs()[1]), new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n",
            StandardOpenOption.CREATE_NEW);
    }
}
