#!/usr/bin/env python3
"""Run Apple actool over a probe suite directory ON a macOS host.

Reads SUITE_DIR/<case>.xcassets plus an optional SUITE_DIR/cases.json for
per-case actool argument overrides, compiles with the real Apple actool into
OUT_DIR/<case>/ and captures: Assets.car, partial plist, stdout, stderr,
exit code, and a per-case summary JSON.

Usage: run_apple_matrix.py SUITE_DIR OUT_DIR [--tool /path/to/actool]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

DEFAULT_ARGS = {
    "basic": ["--platform", "macosx", "--minimum-deployment-target", "13.0"],
    "scales": ["--platform", "iphoneos", "--minimum-deployment-target", "15.0"],
    "colordata": ["--platform", "macosx", "--minimum-deployment-target", "13.0"],
    "brand": ["--platform", "appletvos", "--minimum-deployment-target", "15.0",
              "--app-icon", "Icon", "--target-device", "tv"],
    "tvstack": ["--platform", "appletvos", "--minimum-deployment-target", "15.0"],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tool", default=None, help="explicit actool path; default xcrun actool")
    ns = ap.parse_args()

    shutil.rmtree(ns.out, ignore_errors=True)
    ns.out.mkdir(parents=True, exist_ok=True)

    overrides = {}
    spec = ns.suite / "cases.json"
    if spec.exists():
        overrides = json.loads(spec.read_text())

    results = {}
    for catalog in sorted(ns.suite.glob("*.xcassets")):
        case = catalog.stem
        case_out = ns.out / case
        case_out.mkdir(parents=True, exist_ok=True)
        partial = case_out / "partial.plist"
        args = overrides.get(case, {}).get("args", DEFAULT_ARGS.get(case, ["--platform", "macosx", "--minimum-deployment-target", "13.0"]))
        if ns.tool:
            cmd = [ns.tool, "--compile", str(case_out)]
        else:
            cmd = ["xcrun", "actool", "--compile", str(case_out)]
        cmd += args + ["--output-partial-info-plist", str(partial), str(catalog)]
        proc = subprocess.run(cmd, capture_output=True)
        (case_out / "stdout.bin").write_bytes(proc.stdout)
        (case_out / "stderr.bin").write_bytes(proc.stderr)
        entry = {
            "case": case,
            "command": cmd,
            "exit_code": proc.returncode,
            "files": sorted(p.name for p in case_out.iterdir() if p.is_file()),
        }
        car = case_out / "Assets.car"
        if car.exists():
            data = car.read_bytes()
            entry["car_sha256"] = hashlib.sha256(data).hexdigest()
            entry["car_size"] = len(data)
        if partial.exists():
            entry["partial_utf8"] = partial.read_text("utf-8", "replace")
        results[case] = entry
        print(json.dumps({"case": case, "exit": proc.returncode, "car": "car_sha256" in entry}))
    (ns.out / "matrix-summary.json").write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
