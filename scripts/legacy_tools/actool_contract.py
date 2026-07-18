#!/usr/bin/env python3
"""Capture actool CLI grammar and diagnostics across installed Xcodes."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
import subprocess


def run(args: list[str], env: dict[str, str]) -> dict[str, object]:
    try:
        p = subprocess.run(args, env=env, text=True, capture_output=True, timeout=30)
        return {"args": args, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as exc:
        return {"args": args, "exit_code": 124, "stdout": exc.stdout or "", "stderr": f"timeout: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("actool-contract.json"))
    ns = ap.parse_args()
    rows = []
    for app in sorted(Path("/Applications").glob("Xcode*.app")):
        env = os.environ.copy(); env["DEVELOPER_DIR"] = str(app / "Contents/Developer")
        cases = {
            "xcode-version": ["xcodebuild", "-version"],
            "help": ["xcrun", "actool", "--help"],
            "version": ["xcrun", "actool", "--version"],
            "no-input": ["xcrun", "actool", "--compile", "/tmp/actool-contract-out"],
            "unknown-option": ["xcrun", "actool", "--arena-invalid-option"],
            "missing-input": ["xcrun", "actool", "--compile", "/tmp/actool-contract-out", "/tmp/does-not-exist.xcassets"],
        }
        results = {name: run(command, env) for name, command in cases.items()}
        help_text = str(results["help"]["stdout"]) + str(results["help"]["stderr"])
        rows.append({
            "xcode_app": str(app), "cases": results,
            "help_sha256": hashlib.sha256(help_text.encode()).hexdigest(),
            "help_lines": len(help_text.splitlines()),
        })
    ns.output.write_text(json.dumps({"schema": 1, "rows": rows}, indent=2, sort_keys=True))
    for row in rows:
        version = str(row["cases"]["xcode-version"]["stdout"]).splitlines()
        print((version[0] if version else row["xcode_app"]), row["help_lines"], row["help_sha256"])
    return 0

if __name__ == "__main__": raise SystemExit(main())
