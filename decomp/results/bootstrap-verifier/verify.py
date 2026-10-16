#!/usr/bin/env python3
"""Synthetic-only independent compile/link/compare prototype; no stock matches.

The coordinator creates a trusted oracle once. Candidate verification never
updates expected output, flags or tools. All candidate builds happen afresh.
This is a workflow boundary, NOT a sandbox against a hostile same-UID process.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
FLAGS = ["--target=arm-none-eabi", "-mcpu=arm968e-s", "-march=armv5te",
         "-mthumb", "-mfloat-abi=soft", "-mabi=aapcs", "-std=c11", "-O2",
         "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-fno-lto",
         "-fno-ident", "-fno-common", "-fno-unwind-tables",
         "-fno-asynchronous-unwind-tables", "-nostdinc", "-Wall", "-Wextra", "-Werror"]
LINK_FLAGS = ["-m", "armelf", "--build-id=none", "--no-undefined", "--fatal-warnings"]
ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC", "SOURCE_DATE_EPOCH": "0"}


class Rejected(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise Rejected(f"command failed: {cmd[0]}\n{p.stdout}{p.stderr}")
    return p.stdout


def pin(path):
    path = Path(path).absolute()
    return {"path": str(path), "sha256": sha(path.read_bytes())}


def check_pin(record):
    if sha(Path(record["path"]).read_bytes()) != record["sha256"]:
        raise Rejected("pinned file changed: " + record["path"])


def source_policy(source):
    # Intentionally restricted to simple synthetic C. Macro/escape bans also
    # prevent hiding asm/attributes behind preprocessor concatenation.
    if not source.isascii() or re.search(
        r'#|\\|\b(?:asm|__asm|__asm__|__attribute__|__declspec|_Pragma|__builtin_\w+)\b', source
    ):
        raise Rejected("source policy: directives, asm, attributes or compiler intrinsics")


def elf_view(data):
    """Strict ELF32 LE ARM view: all allocated sections, NOBITS and load segments.

    No relocation masking or byte normalization. Debug/symbol/string tables are
    not runtime bytes. Allocated section metadata and full PT_LOAD bytes count.
    """
    def take(off, size):
        if off < 0 or size < 0 or off + size > len(data):
            raise Rejected("truncated ELF")
        return data[off:off + size]

    if take(0, 7) != b"\x7fELF\x01\x01\x01":
        raise Rejected("expected ELF32 little endian")
    h = struct.unpack("<HHIIIIIHHHHHH", take(16, 36))
    kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = h
    if (kind, machine, version, ehsize, phsize, shsize) != (2, 40, 1, 52, 32, 40):
        raise Rejected("unsupported ELF header")
    if not (0 < shstr < shnum and 0 < shnum < 4096 and 0 < phnum < 256):
        raise Rejected("unsupported ELF table counts")
    sections = [struct.unpack("<IIIIIIIIII", take(shoff + i * shsize, shsize)) for i in range(shnum)]
    names = take(sections[shstr][4], sections[shstr][5])
    allocated = []
    for s in sections:
        nameoff, stype, sflags, address, offset, size, link, info, align, entsize = s
        if nameoff >= len(names):
            raise Rejected("bad ELF section name")
        name = names[nameoff:].split(b"\0", 1)[0].decode("ascii")
        if stype in (4, 9) and size:
            raise Rejected("unresolved relocations in final ELF")
        if sflags & 2:
            contents = b"" if stype == 8 else take(offset, size)
            allocated.append({"name": name, "type": stype, "flags": sflags,
                              "address": address, "size": size, "align": align,
                              "bytes": contents.hex()})
    segments = []
    for i in range(phnum):
        typ, off, va, pa, filesz, memsz, pflags, align = struct.unpack(
            "<IIIIIIII", take(phoff + i * phsize, phsize))
        if typ == 1:
            if filesz > memsz:
                raise Rejected("invalid PT_LOAD sizes")
            segments.append({"vaddr": va, "paddr": pa, "filesz": filesz,
                             "memsz": memsz, "flags": pflags, "align": align,
                             "bytes": take(off, filesz).hex()})
    if not allocated or not segments:
        raise Rejected("empty image")
    return {"entry": entry, "elf_flags": flags, "sections": allocated, "segments": segments}


def build(source, out, lock, linker):
    source_policy(source)
    (out / "candidate.c").write_text(source)
    cc = lock["compiler"]["path"]
    flags = lock["compile_flags"]
    ast = json.loads(run([cc, *flags, "-Xclang", "-ast-dump=json", "-fsyntax-only", "candidate.c"], out))

    def inspect(node):
        kind = node.get("kind", "")
        if "Asm" in kind or kind in ("SectionAttr", "NakedAttr"):
            raise Rejected("source policy: assembly or executable data")
        if kind in ("CStyleCastExpr", "ImplicitCastExpr") and node.get("castKind") != "FunctionToPointerDecay":
            if "(*)" in node.get("type", {}).get("qualType", "").replace(" ", ""):
                raise Rejected("source policy: function pointer casts require review")
        for child in node.get("inner", []):
            inspect(child)
    inspect(ast)
    interface = sorted((node["name"], node["type"]["qualType"])
                       for node in ast.get("inner", [])
                       if node.get("kind") == "FunctionDecl" and not node.get("isImplicit"))
    if "function_interface" in lock and interface != [tuple(x) for x in lock["function_interface"]]:
        raise Rejected("source ABI mismatch")
    run([cc, *flags, "-c", "candidate.c", "-o", "candidate.o"], out)
    run([lock["linker"]["path"], *lock["link_flags"], "-T", str(linker),
         "candidate.o", "-o", "candidate.elf"], out)
    return (out / "candidate.elf").read_bytes(), interface


def init(oracle):
    if oracle.exists():
        raise Rejected("oracle already exists; use a fresh directory, never refresh a reference")
    oracle.mkdir(parents=True)
    cc, ld = shutil.which("clang"), shutil.which("ld.lld")
    if not cc or not ld:
        raise Rejected("clang and ld.lld required for synthetic fixture")
    lock = {"schema_version": 1, "scope": "synthetic-only", "compiler_status": "synthetic-pinned",
            "stock_compiler_status": "unknown", "compile_flags": FLAGS,
            "link_flags": LINK_FLAGS, "compiler": pin(cc), "linker": pin(ld),
            "compiler_version": run([cc, "--version"]), "linker_version": run([ld, "--version"]),
            "verifier_sha256": sha(Path(__file__).read_bytes()),
            "python": pin(sys.executable), "python_version": sys.version,
            "abi": "ELF32 little-endian ARMv5TE, Thumb, AAPCS, soft-float (synthetic choice)",
            "environment": ENV}
    deps = set()
    for binary in (cc, ld, sys.executable):
        for line in run(["/usr/bin/ldd", binary]).splitlines():
            deps.update(re.findall(r"(/[^\s()]+)", line))
    lock["host_libraries"] = [pin(p) for p in sorted(deps)]
    for name in ("reference.c", "layout.ld"):
        data = (HERE / name).read_bytes()
        (oracle / name).write_bytes(data)
        lock[name] = sha(data)
    with tempfile.TemporaryDirectory(prefix="synthetic-reference-") as temp:
        data, interface = build((oracle / "reference.c").read_text(), Path(temp), lock, oracle / "layout.ld")
    lock["function_interface"] = interface
    elf_view(data)  # Fail before recording an unsupported reference.
    (oracle / "reference.elf").write_bytes(data)
    lock["reference.elf"] = sha(data)
    encoded = (json.dumps(lock, sort_keys=True, indent=2) + "\n").encode()
    (oracle / "lock.json").write_bytes(encoded)
    for path in oracle.iterdir():
        path.chmod(0o444)
    oracle.chmod(0o555)
    return sha(encoded)


def load_lock(oracle, expected_hash):
    encoded = (oracle / "lock.json").read_bytes()
    if sha(encoded) != expected_hash:
        raise Rejected("oracle lock hash mismatch")
    lock = json.loads(encoded)
    if lock.get("scope") != "synthetic-only" or lock.get("compiler_status") != "synthetic-pinned":
        raise Rejected("unknown or non-synthetic toolchain cannot certify a match")
    if lock["verifier_sha256"] != sha(Path(__file__).read_bytes()):
        raise Rejected("verifier revision changed")
    if lock["environment"] != ENV or lock["python_version"] != sys.version:
        raise Rejected("runtime environment changed")
    for item in (lock["compiler"], lock["linker"], lock["python"], *lock["host_libraries"]):
        check_pin(item)
    for name in ("reference.c", "layout.ld", "reference.elf"):
        if sha((oracle / name).read_bytes()) != lock[name]:
            raise Rejected("oracle artifact changed: " + name)
    return lock


def verify(oracle, expected_hash, candidate, output):
    lock = load_lock(oracle, expected_hash)
    if candidate.suffix != ".c" or candidate.is_symlink():
        raise Rejected("only a regular C source candidate is accepted")
    source = candidate.read_text()
    output.mkdir(parents=True, exist_ok=False)
    actual, _ = build(source, output, lock, oracle / "layout.ld")
    expected = (oracle / "reference.elf").read_bytes()
    av, ev = elf_view(actual), elf_view(expected)
    if av != ev:
        differences = [key for key in ev if av[key] != ev[key]]
        raise Rejected("linked image mismatch: " + ", ".join(differences))
    # Recheck trusted inputs after the build; no candidate object/image is accepted.
    load_lock(oracle, expected_hash)
    return {"result": "synthetic exact match", "stock_matching_coverage": "unknown",
            "candidate_source_sha256": sha(source.encode()), "lock_sha256": expected_hash,
            "candidate_elf_sha256": sha(actual), "reference_elf_sha256": sha(expected),
            "comparison": "all allocated section metadata/bytes and complete PT_LOAD contents"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    create = sub.add_parser("init-synthetic")
    create.add_argument("oracle", type=Path)
    test = sub.add_parser("verify-synthetic")
    test.add_argument("oracle", type=Path)
    test.add_argument("lock_sha256")
    test.add_argument("candidate", type=Path)
    test.add_argument("output", type=Path)
    args = p.parse_args()
    try:
        if args.command == "init-synthetic":
            print(init(args.oracle.resolve()))
        else:
            print(json.dumps(verify(args.oracle.resolve(), args.lock_sha256,
                                    args.candidate, args.output.resolve()), indent=2))
    except (Rejected, OSError, ValueError, KeyError, struct.error) as exc:
        print("REJECTED: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
