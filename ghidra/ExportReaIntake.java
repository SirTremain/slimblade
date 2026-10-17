// Export exact instructions from a validated disposable project, without analysis.
// @category SlimBlade
import com.google.gson.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.util.HexFormat;

public class ExportReaIntake extends GhidraScript {
    private void require(boolean ok, String why) {
        if (!ok) throw new IllegalStateException(why);
    }
    private String hex(long n) { return String.format("0x%08x", n); }
    public void run() throws Exception {
        require(getScriptArgs().length == 2 && currentProgram != null, "input/output required");
        require(state.getProject().getName().equals("SlimBlade-rea-copy"), "disposable copy required");
        JsonObject admission = JsonParser.parseString(Files.readString(Path.of("/work/admission-result.json"))).getAsJsonObject();
        require(admission.get("status").getAsString().equals("admitted"), "admission required");
        JsonObject selection = JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
        JsonArray functions = new JsonArray();
        for (JsonElement item : selection.getAsJsonArray("tasks")) {
            JsonObject task = item.getAsJsonObject();
            long start = Long.decode(task.get("entry").getAsString());
            long end = Long.decode(task.get("end_exclusive").getAsString());
            Function f = getFunctionAt(toAddr(start));
            require(f != null && f.getBody().getNumAddressRanges() == 1 &&
                    f.getBody().getMinAddress().equals(toAddr(start)) &&
                    f.getBody().getMaxAddress().equals(toAddr(end-1)), "body mismatch");
            JsonObject fn = new JsonObject();
            fn.addProperty("entry", hex(start)); fn.addProperty("end_exclusive", hex(end));
            JsonArray instructions = new JsonArray();
            for (long a = start; a < end;) {
                monitor.checkCancelled();
                Instruction i = getInstructionAt(toAddr(a));
                require(i != null && i.getLength() == 2 && a+2 <= end, "expected complete 16-bit Thumb instruction");
                require(BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                    currentProgram.getRegister("TMode"), toAddr(a), false)), "wrong instruction mode");
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
        JsonObject result = new JsonObject();
        result.add("admission", admission); result.add("functions", functions);
        Files.writeString(Path.of(getScriptArgs()[1]), new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n",
            StandardOpenOption.CREATE_NEW);
    }
}
