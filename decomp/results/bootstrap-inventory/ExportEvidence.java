// Export bytes, listing, references, memory map, analysis options and diagnostics.
// @category SlimBlade
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;

public class ExportEvidence extends GhidraScript {
    private String hex(long x) { return String.format("0x%08x", x); }
    @Override
    public void run() throws Exception {
        Path dir = Path.of(getScriptArgs()[0]);
        Files.createDirectory(dir);
        byte[] bytes = new byte[128112];
        currentProgram.getMemory().getBytes(toAddr(0), bytes);
        Files.write(dir.resolve("database-container.bin"), bytes, StandardOpenOption.CREATE_NEW);
        JsonObject meta = new JsonObject();
        meta.addProperty("schema_version", 2);
        meta.addProperty("default_address_space",
            currentProgram.getAddressFactory().getDefaultAddressSpace().getName());
        meta.addProperty("database_container_sha256", HexFormat.of().formatHex(
            java.security.MessageDigest.getInstance("SHA-256").digest(bytes)));
        JsonArray blocks = new JsonArray();
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            JsonObject row = new JsonObject();
            row.addProperty("name", b.getName());
            row.addProperty("start", hex(b.getStart().getOffset()));
            row.addProperty("end_exclusive", hex(b.getEnd().getOffset() + 1));
            row.addProperty("initialized", b.isInitialized());
            row.addProperty("read", b.isRead()); row.addProperty("write", b.isWrite());
            row.addProperty("execute", b.isExecute()); row.addProperty("volatile", b.isVolatile());
            blocks.add(row);
        }
        meta.add("memory_blocks", blocks);
        meta.add("analysis_options", new GsonBuilder().create().toJsonTree(
            getCurrentAnalysisOptionsAndValues(currentProgram)));
        // A completed headless run is not proof of conflict-free analysis. Keep
        // the database's diagnostics in the frozen packet, including those at
        // addresses that do not currently belong to any discovered function.
        JsonArray diagnostics = new JsonArray();
        for (String type : new String[] { BookmarkType.ERROR, BookmarkType.WARNING }) {
            var bookmarks = currentProgram.getBookmarkManager().getBookmarksIterator(type);
            while (bookmarks.hasNext()) {
                monitor.checkCancelled();
                Bookmark bookmark = bookmarks.next();
                JsonObject row = new JsonObject();
                row.addProperty("address", hex(bookmark.getAddress().getOffset()));
                row.addProperty("address_space", bookmark.getAddress().getAddressSpace().getName());
                row.addProperty("severity", type.equals(BookmarkType.ERROR) ? "error" : "warning");
                row.addProperty("category", bookmark.getCategory());
                row.addProperty("message", bookmark.getComment());
                // Error bookmarks can sit just beyond a truncated function
                // body. Preserve incoming control flow, including fallthrough
                // (which is not necessarily an explicit reference).
                var flowSources = new java.util.TreeSet<String>();
                var incoming = currentProgram.getReferenceManager().getReferencesTo(bookmark.getAddress());
                while (incoming.hasNext()) {
                    Reference ref = incoming.next();
                    if (ref.getReferenceType().isFlow() && ref.getFromAddress().getAddressSpace().equals(
                            bookmark.getAddress().getAddressSpace())) {
                        flowSources.add(hex(ref.getFromAddress().getOffset()));
                    }
                }
                Instruction previous = currentProgram.getListing().getInstructionBefore(bookmark.getAddress());
                if (previous != null && bookmark.getAddress().equals(previous.getFallThrough())) {
                    flowSources.add(hex(previous.getAddress().getOffset()));
                }
                row.add("flow_sources", new GsonBuilder().create().toJsonTree(flowSources));
                diagnostics.add(row);
            }
        }
        meta.add("analysis_diagnostics", diagnostics);
        int instructions = 0, indirectFlows = 0, instructionBytes = 0, definedDataBytes = 0;
        AddressSet classified = new AddressSet();
        try (var out = Files.newBufferedWriter(dir.resolve("listing.txt"), StandardCharsets.UTF_8,
                                              StandardOpenOption.CREATE_NEW)) {
            CodeUnitIterator units = currentProgram.getListing().getCodeUnits(true);
            while (units.hasNext()) {
                monitor.checkCancelled();
                CodeUnit u = units.next();
                if (u.getMinAddress().getOffset() >= bytes.length) continue;
                out.write(hex(u.getMinAddress().getOffset()) + "  " +
                    HexFormat.of().formatHex(u.getBytes()) + "  " + u.toString() + "\n");
                if (u instanceof Instruction inst) {
                    instructions++;
                    instructionBytes += u.getLength();
                    classified.add(u.getMinAddress(), u.getMaxAddress());
                    if (inst.getFlowType().isComputed()) indirectFlows++;
                }
                else if (u instanceof Data data && data.isDefined()) {
                    definedDataBytes += u.getLength();
                    classified.add(u.getMinAddress(), u.getMaxAddress());
                }
            }
        }
        JsonArray refs = new JsonArray();
        AddressIterator sources = currentProgram.getReferenceManager().getReferenceSourceIterator(
            toAddr(0), true);
        while (sources.hasNext()) {
            for (Reference r : currentProgram.getReferenceManager().getReferencesFrom(sources.next())) {
                JsonObject row = new JsonObject();
                row.addProperty("from", r.getFromAddress().toString());
                row.addProperty("to", r.getToAddress().toString());
                row.addProperty("type", r.getReferenceType().toString());
                refs.add(row);
            }
        }
        meta.addProperty("instruction_count", instructions);
        meta.addProperty("instruction_bytes", instructionBytes);
        meta.addProperty("defined_data_bytes", definedDataBytes);
        meta.addProperty("unclassified_bytes", bytes.length - instructionBytes - definedDataBytes);
        JsonArray unknown = new JsonArray();
        AddressSet remaining = new AddressSet(toAddr(0), toAddr(bytes.length - 1)).subtract(classified);
        for (AddressRange range : remaining.getAddressRanges()) {
            JsonObject span = new JsonObject();
            span.addProperty("start", hex(range.getMinAddress().getOffset()));
            span.addProperty("end_exclusive", hex(range.getMaxAddress().getOffset() + 1));
            unknown.add(span);
        }
        meta.add("unclassified_ranges", unknown);
        meta.addProperty("computed_flow_instruction_count", indirectFlows);
        var gson = new GsonBuilder().setPrettyPrinting().create();
        Files.writeString(dir.resolve("metadata.json"), gson.toJson(meta) + "\n", StandardOpenOption.CREATE_NEW);
        Files.writeString(dir.resolve("references.json"), gson.toJson(refs) + "\n", StandardOpenOption.CREATE_NEW);
        println("Exported addressed evidence; container hash " + meta.get("database_container_sha256"));
    }
}
