#!/usr/bin/env python3
"""Run the same fixture through Apple actool and actool-linux, then archive evidence.

This script is intended to run on an authorized Mac. It records commands, exit
status, stdout/stderr, output hashes, and toolchain identity without inspecting
or redistributing Apple binaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import time


def run(command: list[str], cwd: Path) -> dict[str, object]:
    started = time.time()
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_seconds": time.time() - started,
    }


def inventory(root: Path) -> list[dict[str, object]]:
    rows = []
    if not root.exists():
        return rows
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        data = path.read_bytes()
        rows.append({"path": str(path.relative_to(root)), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog", type=Path)
    ap.add_argument("--case", required=True)
    ap.add_argument("--evidence", type=Path, default=Path("oracle-evidence"))
    ap.add_argument("--platform", default="macosx")
    ap.add_argument("--target", default="13.0")
    ns = ap.parse_args()
    case = ns.evidence / ns.case
    apple_out = case / "apple-output"
    apple_out.mkdir(parents=True, exist_ok=True)
    toolchain = run(["xcodebuild", "-version"], Path.cwd())
    command = ["xcrun", "actool", "--compile", str(apple_out), "--platform", ns.platform,
               "--minimum-deployment-target", ns.target, str(ns.catalog.resolve())]
    apple = run(command, Path.cwd())
    evidence = {
        "schema": 1,
        "toolchain": toolchain,
        "apple": apple,
        "apple_inventory": inventory(apple_out),
    }
    (case / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(case / "evidence.json")
    return 0 if apple["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
