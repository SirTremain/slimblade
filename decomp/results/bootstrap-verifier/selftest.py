#!/usr/bin/env python3
"""Exercise the real verifier in separate processes using synthetic controls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path, help="fresh ignored directory")
    args = p.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    oracle = root / "oracle"
    lock_hash = verify.init(oracle)
    reference = (verify.HERE / "reference.c").read_text()
    results = []

    def attempt(name, source, expected, reason="", target=oracle, trusted_hash=lock_hash, prebuilt=False):
        candidate = root / (name + ".c")
        candidate.write_text(source)
        output = root / (name + "-build")
        if prebuilt:
            output.mkdir()
            shutil.copyfile(oracle / "reference.elf", output / "candidate.elf")
        cmd = [sys.executable, str(verify.HERE / "verify.py"), "verify-synthetic",
               str(target), trusted_hash, str(candidate), str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        actual = result.returncode == 0
        detail = result.stdout.strip() if actual else result.stderr.strip()
        if actual != expected or (reason and reason not in detail):
            raise AssertionError(f"{name}: unexpected result: {detail}")
        results.append({"test": name, "passed": True, "candidate_accepted": actual, "detail": detail})

    attempt("positive", reference, True)
    attempt("positive-independent-rebuild", reference + "\n", True)
    for name, old, new in (
        ("wrong-constant", "0x12345678u", "0x12345679u"),
        ("wrong-signedness", "(signed char)*input", "(unsigned char)*input"),
        ("missing-store", "sink = value;", ""),
        ("changed-call", "return external_a(value)", "return external_b(value)"),
        ("changed-rodata", "3, 5, 11, 17", "3, 5, 13, 17"),
        ("changed-data", "0x13579bdfu", "0x13579bdeu"),
        ("changed-bss", "volatile unsigned sink;", "volatile unsigned sink;\nvolatile unsigned extra;"),
    ):
        assert old in reference
        attempt(name, reference.replace(old, new), False, "linked image mismatch")
    attempt("inline-assembly", reference.replace("sink = value;", 'asm("nop");'), False, "source policy")
    attempt("changed-call-prototype", reference.replace("external_a(unsigned)", "external_a(int)"),
            False, "source ABI mismatch")
    attempt("embedded-code", reference + '\nconst unsigned char blob[] __attribute__((section(".text"))) = {0x70, 0x47};\n',
            False, "source policy")
    attempt("executable-data-cast", reference.replace("external_a(value)", "((unsigned (*)(unsigned))table)(value)"),
            False, "source policy")
    attempt("prebuilt-postlink-output", reference, False, "File exists", prebuilt=True)

    def altered_oracle(name, filename, change):
        dest = root / name
        shutil.copytree(oracle, dest)
        dest.chmod(0o755)
        path = dest / filename
        path.chmod(0o644)
        path.write_bytes(change(path.read_bytes()))
        return dest

    damaged = altered_oracle("damaged-reference", "reference.elf", lambda b: b[:-1] + bytes([b[-1] ^ 1]))
    attempt("damaged-target", reference, False, "oracle artifact changed", target=damaged)
    flags = altered_oracle("changed-flags", "lock.json", lambda b: b.replace(b'"-O2"', b'"-O0"'))
    attempt("changed-flags", reference, False, "oracle lock hash mismatch", target=flags)
    unknown = altered_oracle("unknown-toolchain", "lock.json",
                             lambda b: b.replace(b'"synthetic-pinned"', b'"unknown"'))
    attempt("unknown-toolchain", reference, False, "unknown or non-synthetic toolchain",
            target=unknown, trusted_hash=verify.sha((unknown / "lock.json").read_bytes()))
    changed_linker = altered_oracle("changed-linker-script", "layout.ld", lambda b: b.replace(b"0x9001", b"0x9201"))
    attempt("changed-linker-script", reference, False, "oracle artifact changed", target=changed_linker)

    def change_compiler(b):
        data = json.loads(b)
        data["compiler"]["sha256"] = "0" * 64
        return json.dumps(data).encode()
    compiler = altered_oracle("changed-tool", "lock.json", change_compiler)
    attempt("changed-tool", reference, False, "pinned file changed", target=compiler,
            trusted_hash=verify.sha((compiler / "lock.json").read_bytes()))
    image = (oracle / "reference.elf").read_bytes()
    view = verify.elf_view(image)
    text = next(s for s in view["sections"] if s["name"] == ".text")
    if "78563412" not in text["bytes"]:
        raise AssertionError("literal-pool control not present in .text")
    # The call control has identical unrelocated .text and different relocation
    # symbols. This proves the final comparison is not masking relocation bytes.
    objcopy = shutil.which("llvm-objcopy")
    for name in ("positive", "changed-call"):
        verify.run([objcopy, "--dump-section", f".text={root / (name + '-text.bin')}",
                    str(root / (name + "-build") / "candidate.o")])
    if (root / "positive-text.bin").read_bytes() != (root / "changed-call-text.bin").read_bytes():
        raise AssertionError("changed-call object .text was expected to match before relocation")
    results.append({"test": "relocation-control", "passed": True,
                    "detail": "object .text identical; linked changed-call rejected"})
    results.append({"test": "literal-pool-control", "passed": True,
                    "detail": "0x12345678 present in .text; altered constant rejected"})
    report = {"status": "synthetic suite passed", "stock_matching_coverage": "unknown",
              "lock_sha256": lock_hash, "oracle": str(oracle), "tests": results}
    (root / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "tests_passed": len(results),
                      "lock_sha256": lock_hash}, indent=2))


if __name__ == "__main__":
    main()
