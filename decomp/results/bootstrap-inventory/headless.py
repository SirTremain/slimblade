#!/usr/bin/env python3
"""Run pinned Ghidra with all writable Java settings in the local state tree."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("args", nargs=argparse.REMAINDER)
args = parser.parse_args()
state = args.state.resolve()
pins = json.loads((Path(__file__).with_name("artifacts.json")).read_text())
env = os.environ.copy()
env["JAVA_HOME"] = str(state / "tools" / pins["java"]["directory"])
env["PATH"] = env["JAVA_HOME"] + "/bin:" + env.get("PATH", "")
env["XDG_CONFIG_HOME"] = str(state / "settings")
env["XDG_CACHE_HOME"] = str(state / "cache")
options = []
for prop, name in (("user.home", "java-user"), ("application.settingsdir", "settings"),
                   ("application.cachedir", "cache"), ("application.tempdir", "temp")):
    path = state / name
    path.mkdir(exist_ok=True)
    if " " in str(path):
        raise ValueError("Ghidra JVM option paths must not contain spaces")
    options.append(f"-D{prop}={path}")
env["JAVA_TOOL_OPTIONS"] = " ".join(options)
cmd = [str(state / "tools" / pins["ghidra"]["directory"] / "support/analyzeHeadless")]
cmd += args.args[1:] if args.args[:1] == ["--"] else args.args
process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
failed = False
for line in process.stdout:
    print(line, end="", flush=True)
    # Ghidra can exit zero after a Java script exception. Do not report that as
    # a successful setup/export. Preserve all output for diagnosis.
    if "ERROR " in line or "REPORT SCRIPT ERROR" in line or "analysis timed out" in line.lower():
        failed = True
code = process.wait()
raise SystemExit(code or (1 if failed else 0))
