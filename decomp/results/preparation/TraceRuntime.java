// Execute original helper bytes in Ghidra's offline emulator, not a device.
// @category SlimBlade
import com.google.gson.*;
import ghidra.app.script.GhidraScript;
import ghidra.pcode.emu.*;
import ghidra.pcode.exec.*;
import ghidra.pcode.exec.PcodeExecutorStatePiece.Reason;
import ghidra.program.model.lang.RegisterValue;
import java.math.BigInteger;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

public class TraceRuntime extends GhidraScript {
    private void require(boolean ok, String message) { if (!ok) throw new IllegalStateException(message); }
    private long reg(PcodeThread<byte[]> e, String name) {
        if(name.equals("pc")) return e.getCounter().getOffset();
        if(name.equals("TMode")) return e.getContext().getRegisterValue(currentProgram.getRegister(name)).getUnsignedValue().longValue();
        byte[] bytes=e.getState().getVar(currentProgram.getRegister(name),Reason.INSPECT);
        long value=0; for(int i=0;i<bytes.length;i++) value|=(bytes[i]&255L)<<(8*i);
        return value;
    }
    private void put(PcodeThread<byte[]> e,String name,long value) {
        var r=currentProgram.getRegister(name); byte[] b=new byte[r.getMinimumByteSize()];
        for(int i=0;i<b.length;i++) b[i]=(byte)(value>>(8*i)); e.getState().setVar(r,b);
    }
    public void run() throws Exception {
        Path output = Path.of(getScriptArgs()[0]);
        require(!Files.exists(output), "output exists");
        byte[] original = new byte[128112];
        currentProgram.getMemory().getBytes(toAddr(0), original);
        String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original));
        require(sha.equals("e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"), "wrong baseline");
        long[] high = {0, 0x3ff00000L, 0x7fefffffL, 0x7ff00000L, 0x7ff00001L,
            0x7ff80000L, 0x80000000L, 0xbff00000L, 0xffefffffL, 0xfff00000L, 0xfff00001L, 0xfff80000L};
        JsonObject report = new JsonObject(); report.addProperty("baseline_sha256", sha);
        report.addProperty("scope", "original-instruction offline execution; no firmware mutation");
        JsonArray rows = new JsonArray();
        PcodeEmulator machine = new PcodeEmulator(currentProgram.getLanguage());
        machine.getSharedState().setVar(toAddr(0),original.length,false,original);
        PcodeThread<byte[]> e=machine.newThread();
        boolean injected = getScriptArgs().length == 2;
        if (injected) {
            String code = Files.readString(Path.of(getScriptArgs()[1]));
            for (long call : new long[]{0x1e360,0x1e47c})
                e.inject(toAddr(call),code.replace("inst_next",String.format("0x%x:4",call+4)));
        }
        report.addProperty("injected_analysis_model",injected);
        {
            for (long call : new long[]{0x1e360,0x1e47c})
            for (long a : high) for (long b : high)
            for (long lowA : new long[]{0,1,0xffffffffL})
            for (long lowB : new long[]{0,1,0xffffffffL})
            for (long r5 : new long[]{0,0xffe00000L})
            for (int thumb = 0; thumb < 2; thumb++) {
                monitor.checkCancelled();
                long[] inputs = {lowA, a, lowB, b, 0x44444444L, r5, 0x66666666L};
                for (int r=0;r<13;r++) put(e,"r"+r, r<7 ? inputs[r] : 0x12340000L+r);
                for (String flag : new String[]{"NG","ZR","CY","OV","TB"}) put(e,flag,0);
                e.overrideCounter(toAddr(call)); e.overrideContextWithDefault();
                e.overrideContext(new RegisterValue(currentProgram.getRegister("TMode"),BigInteger.ZERO));
                put(e,"sp",0x400800); put(e,"lr",0x2100+thumb);
                long[] saved = {0x14141414,0x15151515,0x16161616,0x2100+thumb};
                for (int n=0;n<4;n++) machine.getSharedState().setInt(toAddr(0x400800+4*n),(int)saved[n]);
                JsonArray trace = new JsonArray(); int index=-1, selector=-1;
                for (int count=0;count<100;count++) {
                    long pc=e.getCounter().getOffset(); trace.add(pc);
                    if (pc==0x1e544) index=(int)reg(e,"r12");
                    if (pc==0x1e550) selector=(int)reg(e,"r6");
                    if (pc==0x1e368 || pc==0x1e36c || pc==0x1e484 || pc==0x1e48c || pc==0x2100) break;
                    require(pc!=0x1e364 && pc!=0x1e480, "inline data executed");
                    require(count<99,"step limit"); e.stepInstruction();
                }
                require(injected || (index>=0 && index<=8 && selector>=0 && selector<=7), "bad selector");
                JsonObject row = new JsonObject(); row.addProperty("call",call);
                JsonArray in = new JsonArray(); for(long value:inputs) in.add(value);
                row.add("inputs",in); row.addProperty("saved_return",0x2100+thumb);
                row.addProperty("index",index); row.addProperty("selector",selector); row.add("trace",trace);
                JsonObject result = new JsonObject();
                for (String name : new String[]{"r0","r1","r2","r3","r4","r5","r6","r12","sp","lr","pc","NG","ZR","CY","OV","TMode"})
                    result.addProperty(name,reg(e,name));
                row.add("result",result); rows.add(row);
            }
        }
        report.add("cases",rows);
        Files.writeString(output,new GsonBuilder().setPrettyPrinting().create().toJson(report)+"\n",StandardOpenOption.CREATE_NEW);
        println("Recorded "+rows.size()+(injected ? " injected analysis-model" : " original-byte helper")+" executions.");
    }
}
