// Export existing function metadata only. Does not analyze or decompile.
// @category SlimBlade

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import ghidra.app.script.GhidraScript;
import ghidra.framework.Application;
import ghidra.program.model.address.AddressRangeIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.lang.Register;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

public class ExportInventory extends GhidraScript {
    private String hex(long value) {
        return String.format("0x%08x", value);
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (currentProgram == null || args.length != 1) {
            throw new IllegalArgumentException("Usage: ExportInventory.java OUTPUT.json");
        }
        JsonObject result = new JsonObject();
        result.addProperty("schema_version", 1);
        result.addProperty("status", "UNREVIEWED_GHIDRA_DISCOVERY");
        result.addProperty("baseline_sha256", currentProgram.getExecutableSHA256());
        result.addProperty("ghidra_version", Application.getApplicationVersion());
        result.addProperty("language", currentProgram.getLanguageID().toString());
        result.addProperty("compiler_spec", currentProgram.getCompilerSpec().getCompilerSpecID().toString());
        JsonArray functions = new JsonArray();
        Register tmode = currentProgram.getRegister("TMode");
        FunctionIterator iterator = currentProgram.getFunctionManager().getFunctions(true);
        while (iterator.hasNext()) {
            monitor.checkCancelled();
            Function function = iterator.next();
            if (function.isExternal()) {
                continue;
            }
            JsonObject row = new JsonObject();
            long entry = function.getEntryPoint().getOffset();
            row.addProperty("id", String.format("fn_%08x", entry));
            row.addProperty("entry", hex(entry));
            row.addProperty("ghidra_name", function.getName());
            BigInteger mode = tmode == null ? null : currentProgram.getProgramContext()
                .getValue(tmode, function.getEntryPoint(), false);
            row.addProperty("mode", mode == null ? "unknown" :
                (mode.equals(BigInteger.ZERO) ? "arm" : "thumb"));
            row.addProperty("thunk", function.isThunk());
            JsonArray ranges = new JsonArray();
            AddressRangeIterator body = function.getBody().getAddressRanges();
            while (body.hasNext()) {
                var range = body.next();
                JsonObject span = new JsonObject();
                span.addProperty("start", hex(range.getMinAddress().getOffset()));
                span.addProperty("end_exclusive", hex(range.getMaxAddress().getOffset() + 1));
                ranges.add(span);
            }
            row.add("ranges", ranges);
            functions.add(row);
        }
        result.add("functions", functions);
        Path output = Path.of(args[0]);
        Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(result) + "\n",
            StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW);
        println("Exported " + functions.size() + " discovered functions; boundaries require review.");
    }
}
