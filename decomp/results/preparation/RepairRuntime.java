// Analysis-only repair, on a fresh copied project; firmware bytes never change.
// @category SlimBlade
import com.google.gson.*;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.database.SpecExtension;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.data.DWordDataType;
import ghidra.program.model.data.MutabilitySettingsDefinition;
import ghidra.program.model.listing.*;
import ghidra.program.model.pcode.JumpTable;
import ghidra.program.model.symbol.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

public class RepairRuntime extends GhidraScript {
    private void require(boolean ok,String message) { if(!ok) throw new IllegalStateException(message); }
    private byte[] bytes() throws Exception {
        byte[] b=new byte[128112]; require(currentProgram.getMemory().getBytes(toAddr(0),b)==b.length,"short input"); return b;
    }
    private String hash(byte[] b) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b)); }
    private void decode(long start,long end) throws Exception {
        currentProgram.getListing().clearCodeUnits(toAddr(start),toAddr(end),false);
        currentProgram.getProgramContext().setValue(currentProgram.getRegister("TMode"),toAddr(start),toAddr(end),BigInteger.ZERO);
        for(long a=start;a<=end;a+=4) {
            if(getInstructionAt(toAddr(a))==null) {
                var cmd=new DisassembleCommand(toAddr(a),new AddressSet(toAddr(start),toAddr(end)),true);
                cmd.enableCodeAnalysis(false); require(cmd.applyTo(currentProgram,monitor),"decode failed "+cmd.getStatusMsg());
            }
            require(getInstructionAt(toAddr(a))!=null,"missing instruction "+Long.toHexString(a));
        }
    }
    private void edge(long from,long to) {
        currentProgram.getReferenceManager().addMemoryReference(toAddr(from),toAddr(to),RefType.COMPUTED_JUMP,SourceType.USER_DEFINED,-1);
    }
    public void run() throws Exception {
        require(state.getProject().getName().startsWith("SlimBlade-v449-runtime-"),"use a fresh runtime analysis copy");
        require(getScriptArgs().length==2,"usage: RepairRuntime.java MODEL.xml NEW_OUTPUT_DIR");
        Path output=Path.of(getScriptArgs()[1]); require(!Files.exists(output),"output exists");
        byte[] before=bytes(); String sha=hash(before);
        require(sha.equals("e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"),"wrong baseline");
        require(getInt(toAddr(0x1e364))==0x3efc7e09 && getInt(toAddr(0x1e480))==0x80492492,"wrong dispatch tables");
        require(getInstructionAt(toAddr(0x1e47c)).getFallThrough().equals(toAddr(0x1e480)),"not pristine prior analysis");
        String xml=Files.readString(Path.of(getScriptArgs()[0]));
        new SpecExtension(currentProgram).addReplaceCompilerSpecExtension(xml,monitor);
        getFunctionAt(toAddr(0x1e4f0)).setCallFixup("slimblade_v449_runtime");
        for(long a:new long[]{0x1e364,0x1e480}) {
            currentProgram.getListing().clearCodeUnits(toAddr(a),toAddr(a+3),false);
            Data word=createData(toAddr(a),DWordDataType.dataType);
            MutabilitySettingsDefinition.DEF.setChoice(word,MutabilitySettingsDefinition.CONSTANT);
            setEOLComment(toAddr(a),"Inline dispatch selectors consumed by 0x1e4f0; not executable fallthrough.");
        }
        decode(0x1e36c,0x1e37b); decode(0x1e484,0x1e48f); decode(0x1e56c,0x1e5a7);
        Function first=getFunctionAt(toAddr(0x1e150));
        AddressSet body=new AddressSet(first.getBody());
        body.delete(toAddr(0x1e364),toAddr(0x1e367)); body.add(toAddr(0x1e36c),toAddr(0x1e37b)); first.setBody(body);
        Function second=getFunctionAt(toAddr(0x1e420)); body=new AddressSet(second.getBody());
        body.add(toAddr(0x1e484),toAddr(0x1e48f)); second.setBody(body);
        Function helper=getFunctionAt(toAddr(0x1e4f0)); body=new AddressSet(helper.getBody());
        body.add(toAddr(0x1e56c),toAddr(0x1e5a7)); helper.setBody(body);
        for(long call:new long[]{0x1e360,0x1e47c}) {
            getInstructionAt(toAddr(call)).setFallThrough(null);
            setEOLComment(toAddr(call),"Analysis callfixup models the saved-frame pop, selectors and both continuation/outer-return exits; see preparation evidence.");
        }
        edge(0x1e360,0x1e368); edge(0x1e360,0x1e36c);
        edge(0x1e47c,0x1e484); edge(0x1e47c,0x1e48c);
        new JumpTable(toAddr(0x1e360),new ArrayList<>(List.of(toAddr(0x1e368),toAddr(0x1e36c))),true,0).writeOverride(first);
        new JumpTable(toAddr(0x1e47c),new ArrayList<>(List.of(toAddr(0x1e484),toAddr(0x1e48c))),true,0).writeOverride(second);
        for(long target:new long[]{0x1e56c,0x1e570,0x1e574,0x1e578}) edge(0x1e564,target);
        require(Arrays.equals(before,bytes()),"firmware changed");
        Bookmark[] errors=currentProgram.getBookmarkManager().getBookmarks(toAddr(0x1e480),BookmarkType.ERROR);
        require(errors.length==1 && errors[0].getCategory().equals("Bad Instruction"),"unexpected diagnostic");
        currentProgram.getBookmarkManager().removeBookmark(errors[0]);
        Files.createDirectory(output);
        JsonObject audit=new JsonObject(); audit.addProperty("container_sha256",sha);
        audit.addProperty("firmware_bytes_changed",false); audit.addProperty("model_xml_sha256",hash(xml.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        JsonArray decomp=new JsonArray();
        DecompInterface d=new DecompInterface(); require(d.openProgram(currentProgram),"decompiler open failed");
        try {
            for(long entry:new long[]{0x1e150,0x1e420}) {
                DecompileResults result=d.decompileFunction(getFunctionAt(toAddr(entry)),60,monitor);
                require(result.decompileCompleted() && result.getDecompiledFunction()!=null,"decompile failed "+result.getErrorMessage());
                String text=result.getDecompiledFunction().getC();
                Files.writeString(output.resolve(String.format("fn_%08x.c.txt",entry)),text,StandardOpenOption.CREATE_NEW);
                JsonObject row=new JsonObject(); row.addProperty("entry",String.format("0x%08x",entry));
                row.addProperty("message",result.getErrorMessage()); row.addProperty("pseudocode_sha256",hash(text.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
                decomp.add(row);
            }
        } finally { d.dispose(); }
        audit.add("caller_decompilation",decomp);
        Files.writeString(output.resolve("audit.json"),new GsonBuilder().setPrettyPrinting().create().toJson(audit)+"\n",StandardOpenOption.CREATE_NEW);
        println("Applied verified runtime analysis model; original firmware hash unchanged.");
    }
}
