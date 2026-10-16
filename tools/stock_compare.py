#!/usr/bin/env python3
"""Pinned leaf-pilot C build and exact stock-range feedback, NOT certification.

No device access, assembly, prebuilt candidates, relocations masked, padding
inserted to match size, or whole-image claim. Coordinator owns the lock.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "decomp/results/bootstrap-verifier/verify.py"
spec = importlib.util.spec_from_file_location("synthetic_verifier", PROTOTYPE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
Rejected = base.Rejected
FLAGS = base.FLAGS + ["-fno-strict-aliasing", "-fno-jump-tables"]
LINK_FLAGS = base.LINK_FLAGS + ["--orphan-handling=error"]
SCOPE = "stock-leaf-pilot-feedback-v1"


def require(ok, message):
    if not ok:
        raise Rejected(message)


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def layout(task):
    entry = int(task["entry"], 16)
    require(re.fullmatch(r"fn_[0-9a-f]{8}", task["id"]), "invalid symbol")
    require(task["id"] == f"fn_{entry:08x}", "symbol/entry mismatch")
    # No GC: surplus executable code, constants or writable state must fail.
    # ARM unwind tables carry compiler metadata, not stock executable bytes;
    # explicitly discarded here. Leaf workers may not use unwinding or calls.
    return f"""ENTRY({task['id']})
PHDRS {{ code PT_LOAD FLAGS(5); }}
SECTIONS {{
 .text 0x{entry:x} : SUBALIGN(2) {{ *(.text .text.*) }} :code
 /DISCARD/ : {{ *(.ARM.exidx* .ARM.extab* .comment .note* .ARM.attributes) }}
 .symtab 0 : {{ *(.symtab) }}
 .strtab 0 : {{ *(.strtab) }}
 .shstrtab 0 : {{ *(.shstrtab) }}
}}
"""


def tool_lock():
    cc, ld = shutil.which("clang"), shutil.which("ld.lld")
    require(cc and ld, "clang and ld.lld required")
    deps = set()
    for binary in (cc, ld, sys.executable):
        for line in base.run(["/usr/bin/ldd", binary]).splitlines():
            deps.update(re.findall(r"(/[^\s()]+)", line))
    return {"compiler": base.pin(cc), "linker": base.pin(ld),
            "python": base.pin(sys.executable), "python_version": sys.version,
            "compiler_version": base.run([cc, "--version"]),
            "linker_version": base.run([ld, "--version"]),
            "host_libraries": [base.pin(p) for p in sorted(deps)],
            "compile_flags": FLAGS, "link_flags": LINK_FLAGS,
            "environment": base.ENV,
            "verifier_sha256": base.sha(Path(__file__).read_bytes()),
            "prototype_sha256": base.sha(PROTOTYPE.read_bytes())}


def initialize(root, inventory, destination):
    require(not destination.exists(), "lock exists; never refresh an oracle in place")
    baseline = json.loads((root / "decomp/baseline.json").read_text())
    image = root / ".decomp/stock/stock-v4.49.bin"
    raw = image.read_bytes()
    require(base.sha(raw) == baseline["sha256"] and len(raw) == baseline["bytes"],
            "stock image identity mismatch")
    tasks = json.loads(inventory.read_text())["functions"]
    require(tasks, "no reviewed pilot tasks")
    entries = {}
    for task in tasks:
        require(task.get("comparison_scope") == SCOPE and task["mode"] == "thumb",
                "only reviewed Thumb leaf pilot tasks supported")
        require(len(task["ranges"]) == 1, "shared/discontiguous ownership unsupported")
        start, end = (int(task["ranges"][0][k], 16) for k in ("start", "end_exclusive"))
        require(start == int(task["entry"], 16) and 0 <= start < end <= len(raw), "bad range")
        entries[task["id"]] = {"entry": task["entry"], "end_exclusive": hex(end),
                               "mode": "thumb", "expected_sha256": base.sha(raw[start:end]),
                               "layout": layout(task), "task_sha256": base.sha(encode(task))}
    lock = {**tool_lock(), "schema_version": 1, "scope": SCOPE,
            "original_compiler_status": "unknown",
            "abi": "candidate ARMv5TE Thumb AAPCS soft-float; not historical provenance",
            "baseline": base.pin(image), "baseline_bytes": len(raw), "tasks": entries}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encode(lock))
    destination.chmod(0o444)
    return base.sha(destination.read_bytes())


def load_lock(path, expected_hash):
    data = path.read_bytes()
    require(base.sha(data) == expected_hash, "lock hash mismatch")
    lock = json.loads(data)
    require(lock["scope"] == SCOPE, "unsupported comparison scope")
    require(lock["compile_flags"] == FLAGS and lock["link_flags"] == LINK_FLAGS, "flags changed")
    require(lock["environment"] == base.ENV and lock["python_version"] == sys.version,
            "runtime changed")
    require(lock["verifier_sha256"] == base.sha(Path(__file__).read_bytes()) and
            lock["prototype_sha256"] == base.sha(PROTOTYPE.read_bytes()), "verifier changed")
    for p in (lock["compiler"], lock["linker"], lock["python"], lock["baseline"], *lock["host_libraries"]):
        base.check_pin(p)
    require(Path(lock["baseline"]["path"]).stat().st_size == lock["baseline_bytes"], "baseline size changed")
    return lock


def leaf_policy(ast, symbol):
    functions = [n for n in ast.get("inner", []) if n.get("kind") == "FunctionDecl"]
    require(len(functions) == 1 and functions[0].get("name") == symbol and
            any(n.get("kind") == "CompoundStmt" for n in functions[0].get("inner", [])),
            "exactly the assigned function definition is required")
    require(not any(n.get("kind") == "VarDecl" for n in ast.get("inner", [])),
            "global data not supported by leaf pilot")

    def walk(node):
        require(node.get("kind") not in ("CallExpr", "GCCAsmStmt", "MSAsmStmt", "StringLiteral"),
                "calls, assembly and strings not supported by leaf pilot")
        require(not (node.get("kind") == "VarDecl" and node.get("storageClass") in ("static", "extern")),
                "nonlocal data not supported by leaf pilot")
        require(node.get("castKind") not in ("IntegralToPointer", "PointerToIntegral"),
                "absolute addresses require coordinator review")
        for child in node.get("inner", []):
            walk(child)
    walk(ast)


def compile_leaf(source, out, lock, symbol, script):
    base.source_policy(source)
    # One immutable source snapshot used for AST validation and compilation.
    (out / "candidate.c").write_text(source)
    ast = json.loads(base.run([lock["compiler"]["path"], *lock["compile_flags"],
                              "-Xclang", "-ast-dump=json", "-fsyntax-only", "candidate.c"], out))
    leaf_policy(ast, symbol)
    script_path = out / "layout.ld"
    script_path.write_text(script)
    elf, interface = base.build(source, out, lock, script_path)
    return elf, interface


def runtime_bytes(elf, entry):
    view = base.elf_view(elf)
    require(view["entry"] == entry | 1, "wrong Thumb entry")
    nonempty = [s for s in view["sections"] if s["size"]]
    require(len(nonempty) == 1, "extra allocated code/data/BSS is forbidden")
    section = nonempty[0]
    require(section["name"] == ".text" and section["type"] == 1 and
            section["flags"] == 6 and section["address"] == entry, "wrong runtime section")
    data = bytes.fromhex(section["bytes"])
    # Explicit PHDRS excludes ELF headers and file alignment padding. Require
    # exactly that complete executable segment, not only a convenient section.
    require(len(view["segments"]) == 1, "extra load segments")
    segment = view["segments"][0]
    require(segment["vaddr"] == entry and segment["paddr"] == entry and
            segment["filesz"] == len(data) and segment["memsz"] == len(data) and
            segment["flags"] == 5 and segment["bytes"] == data.hex(), "unexpected load mapping")
    return data


def compare(expected, actual, start):
    differences = [{"address": hex(start + i),
                    "expected": expected[i] if i < len(expected) else None,
                    "actual": actual[i] if i < len(actual) else None}
                   for i in range(max(len(expected), len(actual)))
                   if expected[i:i+1] != actual[i:i+1]]
    return {"result": "exact-range-bytes" if expected == actual else "mismatch",
            "expected_bytes": len(expected), "actual_bytes": len(actual),
            "differing_bytes": len(differences), "first_differences": differences[:64]}


def verify(lock_path, lock_hash, task_id, candidate, output):
    lock = load_lock(lock_path, lock_hash)
    require(task_id in lock["tasks"], "task not in pinned pilot")
    require(candidate.suffix == ".c" and candidate.is_file() and not candidate.is_symlink(),
            "regular C source required; prebuilt outputs are not accepted")
    task = lock["tasks"][task_id]
    start, end = int(task["entry"], 16), int(task["end_exclusive"], 16)
    expected = Path(lock["baseline"]["path"]).read_bytes()[start:end]
    require(base.sha(expected) == task["expected_sha256"], "expected range changed")
    source = candidate.read_text()
    # Always build in a fresh private temporary directory; caller output is
    # diagnostic material, never an input oracle or a prebuilt candidate.
    require(not output.exists(), "output already exists")
    with tempfile.TemporaryDirectory(prefix="slimblade-compare-") as temp:
        build_dir = Path(temp)
        elf, interface = compile_leaf(source, build_dir, lock, task_id, task["layout"])
        actual = runtime_bytes(elf, start)
        result = {**compare(expected, actual, start), "task": task_id,
                  "scope": SCOPE, "certified_match": False,
                  "matching_coverage": "unknown", "original_compiler_status": "unknown",
                  "source_sha256": base.sha(source.encode()), "lock_sha256": lock_hash,
                  "elf_sha256": base.sha(elf), "interface": interface}
        load_lock(lock_path, lock_hash)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(build_dir, output)
        (output / "comparison.json").write_bytes(encode(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="coordinator only; freeze a NEW pilot lock")
    init.add_argument("--root", type=Path, default=ROOT)
    init.add_argument("--inventory", type=Path, required=True)
    init.add_argument("--output", type=Path, required=True)
    for command in ("check", "verify"):
        p = sub.add_parser(command)
        p.add_argument("--lock", type=Path, required=True)
        p.add_argument("--lock-sha256", required=True)
        if command == "verify":
            p.add_argument("--task", required=True)
            p.add_argument("--source", type=Path, required=True)
            p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            print(initialize(args.root.resolve(), args.inventory, args.output))
        elif args.command == "check":
            lock = load_lock(args.lock, args.lock_sha256)
            print(f"Pinned comparison ready: {len(lock['tasks'])} leaves; original compiler unknown")
        else:
            result = verify(args.lock, args.lock_sha256, args.task, args.source, args.output)
            print(json.dumps(result, indent=2))
            return 0 if result["result"] == "exact-range-bytes" else 2
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
